import asyncio
from enum import Enum
from typing import Any
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

from ruter_chatbot.stores.providers.base_provider import BaseProvider
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.types.iac.provider_spec import ProviderSpec
from ruter_chatbot.types.iac.embed_spec import EmbedSpec

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
    """

    def __init__(
        self,
        *,
        name: str,
        provider: BaseProvider,
        embeddings: EmbedSpec,
    ) -> None:
        self.name = name
        self.provider = provider
        self.embeddings = embeddings

        self._state: VectorStoreState = VectorStoreState.INITIALIZING
        self._active_index: FAISS | None = None

        self._lock = asyncio.Lock()
        self._refresh_task: asyncio.Task | None = None

    @classmethod
    def from_spec(cls, spec: VectorStoreSpec) -> "VectorStore":
        provider = BaseProvider.from_spec(spec.provider)

        embed_type = spec.embedder.type
        embed_args = dict(spec.embedder.args)

        # This is in meantime we wait for AWS access.
        if embed_type != "ollama":
            raise ValueError(f"Unsupported embedder type: {embed_type}")

        embed_model = embed_args.pop("model", None)

        if not embed_model:
            raise ValueError("EmbedSpec.args must include 'model'")

        embeddings = OllamaEmbeddings(model=embed_model, **embed_args)

        return cls(
            name=spec.name,
            provider=provider,
            embeddings=embeddings,
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

    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        """
        Synchronous search against the current FAISS index.
        """
        index = self._active_index

        if index is None:
            raise RuntimeError(f"VectorStore '{self.name}' is not ready")

        return index.similarity_search(query, k=k)

    async def initialize(self) -> None:
        """
        Build the first active index.
        """
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
        """
        Rebuild the index and swap when ready.
        """
        task = await self.start_refresh()
        await task

    async def start_refresh(self) -> asyncio.Task:
        """
        Launch refresh in the background.
        """
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
        """
        Internal refresh pipeline.
        """
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
        """
        Collect documents from provider and build a FAISS index.
        """
        sources = self.provider.list_sources()

        docs: list[Document] = []

        for source in sources:
            source_docs: list[Document] = self.provider.get_docs_from_source(source)
            docs.extend(source_docs)

        return self._build_faiss_index(docs)

    def _build_faiss_index(self, docs: list[Document]) -> FAISS:
        if not docs:
            raise ValueError(
                f"VectorStore '{self.name}' could not build index: no documents found"
            )

        return FAISS.from_documents(docs, self.embeddings)



if __name__ == "__main__":
    # Example
    # ------------------------------------------------------------
    # Helper to create test files
    # ------------------------------------------------------------

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


    # ------------------------------------------------------------
    # Main test
    # ------------------------------------------------------------

    async def main() -> None:
        data_dir = ensure_test_data()

        spec = VectorStoreSpec(
            name="test_store",
            provider=ProviderSpec(
                type="filesystem",
                args={
                    "path": str(data_dir),
                    "glob": "*.txt",
                },
            ),
            embedder=EmbedSpec(
                type="ollama",
                args={
                    "model": "nomic-embed-text",
                    "temperature": 0.2
                },
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

        results = store.similarity_search("Hva handler dokumentene om?", k=3)

        print("\nSearch results:")
        for r in results:
            print("-", r.page_content[:100])

        print("\nRunning refresh...")
        await store.refresh()

        print("State after refresh:", store.state)
    
    asyncio.run(main())