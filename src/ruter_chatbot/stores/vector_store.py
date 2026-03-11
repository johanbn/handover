import asyncio
import subprocess
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

from ruter_chatbot.stores.providers.base_provider import BaseProvider
from ruter_chatbot.stores.smart_chunker import SmartChunker


class VectorStoreState(str, Enum):
    INITIALIZING = "initializing"
    READY = "ready"
    REFRESHING = "refreshing"
    FAILED = "failed"


class VectorStore:
    """
    Stateful runtime service for document retrieval + FAISS index lifecycle.

    Design
    ------
    • built from declarative spec via from_spec()
    • holds one active FAISS index at a time
    • initialize() builds the first index
    • refresh() rebuilds a new index beside the old one
    • swap happens only when the new index is ready
    • searches always use the current active index
    • optional daily refresh loop can run in the background
    """

    def __init__(
        self,
        *,
        name: str,
        provider: BaseProvider,
        embeddings: Any,
        chunker: SmartChunker,
    ) -> None:
        self.name = name
        self.provider = provider
        self.embeddings = embeddings
        self.chunker = chunker

        self._state: VectorStoreState = VectorStoreState.INITIALIZING
        self._active_index: FAISS | None = None

        self._lock = asyncio.Lock()
        self._refresh_task: asyncio.Task | None = None
        self._daily_refresh_task: asyncio.Task | None = None

    @classmethod
    def from_spec(cls, spec: "VectorStoreSpec") -> "VectorStore":
        provider = BaseProvider.from_spec(spec.provider)

        embed_type = spec.embedder.type
        embed_args = spec.embedder.args

        if embed_type != "ollama":
            raise ValueError(f"Unsupported embedder type: {embed_type}")

        if not embed_args.get("model"):
            raise ValueError("EmbedSpec.args must include 'model'")

        
        model_name = embed_args["model"]
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if model_name not in result.stdout:
            subprocess.run(["ollama", "pull", model_name], check=True)

        embeddings = OllamaEmbeddings(**embed_args)

        chunker = SmartChunker.from_spec(spec.chunker)

        return cls(
            name=spec.name,
            provider=provider,
            embeddings=embeddings,
            chunker=chunker,
        )

    @property
    def state(self) -> VectorStoreState:
        return self._state

    @property
    def is_ready(self) -> bool:
        return self._active_index is not None and self._state in {
            VectorStoreState.READY,
            VectorStoreState.REFRESHING,
        }

    @property
    def is_refreshing(self) -> bool:
        return self._state == VectorStoreState.REFRESHING

    def _require_active_index(self) -> FAISS:
        index = self._active_index
        if index is None:
            raise RuntimeError(f"VectorStore '{self.name}' is not ready")
        return index

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        *,
        with_score: bool = False,
        **kwargs: Any,
    ) -> list[Document] | list[tuple[Document, float]]:
        index = self._require_active_index()

        if with_score:
            return index.similarity_search_with_score(query, k=k, **kwargs)

        return index.similarity_search(query, k=k, **kwargs)

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> list[Document]:
        index = self._require_active_index()
        return index.max_marginal_relevance_search(
            query,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
        )

    async def initialize(self) -> None:
        async with self._lock:
            if self._active_index is not None:
                return

            self._state = VectorStoreState.INITIALIZING

        try:
            new_index = await self._build_index_from_provider()

            async with self._lock:
                self._active_index = new_index
                self._state = VectorStoreState.READY

        except Exception:
            async with self._lock:
                self._state = VectorStoreState.FAILED
            raise

    async def refresh(self) -> None:
        task = await self.start_refresh()
        await task

    async def start_refresh(self) -> asyncio.Task:
        async with self._lock:
            if self._active_index is None:
                raise RuntimeError(
                    f"VectorStore '{self.name}' cannot refresh before initialization"
                )

            if self._refresh_task and not self._refresh_task.done():
                raise RuntimeError(
                    f"VectorStore '{self.name}' refresh already running"
                )

            self._state = VectorStoreState.REFRESHING

            self._refresh_task = asyncio.create_task(
                self._refresh_impl(),
                name=f"{self.name}-refresh",
            )

            return self._refresh_task

    async def _refresh_impl(self) -> None:
        try:
            new_index = await self._build_index_from_provider()

            async with self._lock:
                self._active_index = new_index
                self._state = VectorStoreState.READY

        except Exception:
            async with self._lock:
                self._state = (
                    VectorStoreState.READY
                    if self._active_index is not None
                    else VectorStoreState.FAILED
                )
            raise

    async def _build_index_from_provider(self) -> FAISS:
        sources = self.provider.list_sources()

        docs: list[Document] = []
        ids: list[str] = []

        for source in sources:
            source_docs: list[Document] = self.provider.get_docs_from_source(source)

            chunk_counter = 0
            for source_doc in source_docs:
                chunked_docs = self.chunker.split_documents(source_doc)

                for chunk_doc in chunked_docs:
                    metadata = chunk_doc.metadata
                    doc_id = f"{source.location}#chunk-{chunk_counter}"

                    metadata["doc_id"] = doc_id
                    chunk_doc.metadata = metadata

                    docs.append(chunk_doc)
                    ids.append(doc_id)

                    chunk_counter += 1

        return self._build_faiss_index(docs, ids)

    def _build_faiss_index(self, docs: list[Document], ids: list[str]) -> FAISS:
        if not docs:
            raise ValueError(
                f"VectorStore '{self.name}' could not build index: no documents found"
            )

        return FAISS.from_documents(docs, self.embeddings, ids=ids)

    def start_daily_refresh_loop(
        self, hour: int = 4, minute: int = 30
    ) -> asyncio.Task:
        if self._daily_refresh_task and not self._daily_refresh_task.done():
            raise RuntimeError(
                f"VectorStore '{self.name}' daily refresh loop already running"
            )

        self._daily_refresh_task = asyncio.create_task(
            self._daily_refresh_loop(hour=hour, minute=minute),
            name=f"{self.name}-daily-refresh-loop",
        )
        return self._daily_refresh_task

    async def stop_daily_refresh_loop(self) -> None:
        task = self._daily_refresh_task
        if task is None:
            return

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            self._daily_refresh_task = None

    async def _daily_refresh_loop(self, hour: int = 4, minute: int = 30) -> None:
        try:
            while True:
                wait_seconds = self._seconds_until_next_refresh(
                    hour=hour,
                    minute=minute,
                )
                print(
                    f"[{self.name}] Next scheduled refresh in "
                    f"{wait_seconds / 3600:.2f} hours"
                )

                await asyncio.sleep(wait_seconds)

                print(f"[{self.name}] Running scheduled refresh...")
                try:
                    await self.refresh()
                    print(f"[{self.name}] Scheduled refresh completed")
                except Exception as exc:
                    print(f"[{self.name}] Scheduled refresh failed: {exc}")

        except asyncio.CancelledError:
            print(f"[{self.name}] Daily refresh loop cancelled")
            raise

    @staticmethod
    def _seconds_until_next_refresh(hour: int, minute: int) -> float:
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if now >= target:
            target = target + timedelta(days=1)

        return (target - now).total_seconds()


if __name__ == "__main__":
    from ruter_chatbot.types.iac.embed_spec import EmbedSpec
    from ruter_chatbot.types.iac.provider_spec import ProviderSpec
    from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec
    from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec

    def ensure_test_data() -> Path:
        data_dir = Path("./src/ruter_chatbot/stores/data")
        data_dir.mkdir(exist_ok=True)

        (data_dir / "doc1.txt").write_text(
            "Ruter er kollektivselskapet i Oslo og Akershus.",
            encoding="utf-8",
        )

        (data_dir / "doc2.txt").write_text(
            "Denne teksten brukes for å teste FAISS vector store refresh.",
            encoding="utf-8",
        )

        return data_dir

    async def main() -> None:
        data_dir = ensure_test_data()

        from ruter_chatbot.specs.providers import ruterwiki_ks

        # use this provider for quick test 
        simple_test=ProviderSpec(
            type="filesystem",
            args={
                "path": str(data_dir),
                "glob": "*.txt",
                }
            )
        
        spec = VectorStoreSpec(
            name="test_store",
            provider=simple_test, #ruterwiki_ks, # uses ruterwiki
            embedder=EmbedSpec(
                type="ollama",
                args={
                    "model": "nomic-embed-text",
                    "temperature": 0.2,
                },
            ),
            chunker=SmartChunkerSpec(
                max_chunk_size=400,
                max_overlap=200,
                semantic_min=120,
                tolerance=0.2,
            ),
        )

        store = VectorStore.from_spec(spec)

        print("Initial state:", store.state)

        try:
            store.similarity_search("test")
        except RuntimeError as exc:
            print("Expected failure before initialize:", exc)

        await store.initialize()

        print("State after initialize:", store.state)

        print("\nStarting daily refresh loop...")
        store.start_daily_refresh_loop(hour=4, minute=30)

        results = store.similarity_search(
            "Hva handler dokumentene om?",
            k=3,
        )

        print("\nSimilarity search results:")
        for result in results:
            print("-", result.page_content[:100], "|", result.metadata)

        scored_results = store.similarity_search(
            "Hva handler dokumentene om?",
            k=3,
            with_score=True,
        )

        print("\nSimilarity search results (with score):")
        for doc, score in scored_results:
            print(f"- score={score:.4f} | {doc.page_content[:100]} | {doc.metadata}")

        mmr_results = store.max_marginal_relevance_search(
            "Hva handler dokumentene om?",
            k=3,
            fetch_k=10,
            lambda_mult=0.5,
        )

        print("\nMMR search results:")
        for result in mmr_results:
            print("-", result.page_content[:100], "|", result.metadata)

        print("\nRunning refresh...")
        refresh_task = await store.start_refresh()

        print("State during refresh:", store.state)

        await refresh_task

        print("State after refresh:", store.state)

        try:
            await asyncio.sleep(5)
        finally:
            print("\nStopping daily refresh loop...")
            await store.stop_daily_refresh_loop()

    asyncio.run(main())