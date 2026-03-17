import subprocess
import threading
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import boto3
from tqdm import tqdm

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings
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
    Thread-based runtime service for document retrieval + FAISS index lifecycle.

    Lifecycle
    ---------
    - from_spec() creates the store
    - initialize() builds the first index (blocking)
    - refresh() rebuilds and swaps in a new index (blocking)
    - start_refresh() rebuilds and swaps in a new index (background thread)
    - start_daily_refresh_loop() runs recurring background refresh
    - searches always use the current active index
    - active index is only swapped when the new one is fully built
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

        self._lock = threading.RLock()

        self._refresh_thread: threading.Thread | None = None
        self._daily_refresh_thread: threading.Thread | None = None
        self._daily_refresh_stop_event = threading.Event()

    @classmethod
    def from_spec(cls, spec: "VectorStoreSpec") -> "VectorStore":
        print(
            f"Creating VectorStore "
            f"name={spec.name} "
            f"embedder_type={spec.embedder.type} "
            f"embedder_args={spec.embedder.args}"
        )

        provider = BaseProvider.from_spec(spec.provider)
        embeddings = cls._build_embeddings_from_spec(spec.embedder)
        chunker = SmartChunker.from_spec(spec.chunker)

        print(
            f"[{spec.name}] Created embeddings instance: "
            f"{type(embeddings).__name__}"
        )

        return cls(
            name=spec.name,
            provider=provider,
            embeddings=embeddings,
            chunker=chunker,
        )

    @staticmethod
    def _build_embeddings_from_spec(embed_spec: "EmbedSpec") -> Any:
        embed_type = embed_spec.type
        embed_args = dict(embed_spec.args)

        if embed_type == "ollama":
            model_name = embed_args.get("model")
            if not model_name:
                raise ValueError("EmbedSpec.args must include 'model' for ollama")

            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=False,
            )

            if model_name not in result.stdout:
                subprocess.run(["ollama", "pull", model_name], check=True)

            return OllamaEmbeddings(**embed_args)

        if embed_type == "bedrock":
            model_id = embed_args.pop("model_id", None)
            region_name = embed_args.pop("region_name", "eu-west-1")

            if not model_id:
                raise ValueError(
                    "EmbedSpec.args must include 'model_id' for bedrock"
                )

            client = boto3.client(
                service_name="bedrock-runtime",
                region_name=region_name,
            )

            return BedrockEmbeddings(
                client=client,
                model_id=model_id,
                **embed_args,
            )

        raise ValueError(f"Unsupported embedder type: {embed_type}")

    @property
    def state(self) -> VectorStoreState:
        with self._lock:
            return self._state

    @property
    def is_ready(self) -> bool:
        with self._lock:
            return self._active_index is not None and self._state in {
                VectorStoreState.READY,
                VectorStoreState.REFRESHING,
            }

    @property
    def is_refreshing(self) -> bool:
        with self._lock:
            return self._state == VectorStoreState.REFRESHING

    @property
    def is_background_refresh_running(self) -> bool:
        thread = self._refresh_thread
        return thread is not None and thread.is_alive()

    @property
    def is_daily_refresh_running(self) -> bool:
        thread = self._daily_refresh_thread
        return thread is not None and thread.is_alive()

    def _require_active_index(self) -> FAISS:
        with self._lock:
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

    def initialize(self) -> None:
        """
        Blocking initialization.
        Safe to call multiple times; only the first successful call builds the index.
        """
        with self._lock:
            if self._active_index is not None:
                return
            self._state = VectorStoreState.INITIALIZING

        self._rebuild_and_swap(failure_state=VectorStoreState.FAILED)

    def refresh(self) -> None:
        """
        Blocking one-shot refresh.
        Searches continue using the old index while refresh is running.
        """
        self._prepare_refresh()
        self._rebuild_and_swap(failure_state=VectorStoreState.READY)

    def start_refresh(self) -> threading.Thread:
        """
        Start a background one-shot refresh.
        Returns the worker thread.
        """
        self._prepare_refresh()

        thread = threading.Thread(
            target=self._refresh_thread_entrypoint,
            name=f"{self.name}-refresh",
            daemon=True,
        )

        with self._lock:
            self._refresh_thread = thread

        thread.start()
        return thread

    def start_daily_refresh_loop(
        self,
        hour: int = 4,
        minute: int = 30,
    ) -> threading.Thread:
        """
        Start a recurring background refresh loop.
        The loop waits until the next scheduled time, then runs a blocking refresh
        inside its own worker thread.
        """
        with self._lock:
            if self._daily_refresh_thread and self._daily_refresh_thread.is_alive():
                raise RuntimeError(
                    f"VectorStore '{self.name}' daily refresh loop already running"
                )

            self._daily_refresh_stop_event.clear()

            thread = threading.Thread(
                target=self._daily_refresh_loop,
                kwargs={"hour": hour, "minute": minute},
                name=f"{self.name}-daily-refresh-loop",
                daemon=True,
            )
            self._daily_refresh_thread = thread

        thread.start()
        return thread

    def stop_daily_refresh_loop(self, timeout: float | None = None) -> None:
        thread = self._daily_refresh_thread
        if thread is None:
            return

        self._daily_refresh_stop_event.set()
        thread.join(timeout=timeout)

        with self._lock:
            if self._daily_refresh_thread is thread and not thread.is_alive():
                self._daily_refresh_thread = None

    def _prepare_refresh(self) -> None:
        with self._lock:
            if self._active_index is None:
                raise RuntimeError(
                    f"VectorStore '{self.name}' cannot refresh before initialization"
                )

            if self._refresh_thread and self._refresh_thread.is_alive():
                raise RuntimeError(
                    f"VectorStore '{self.name}' refresh already running"
                )

            self._state = VectorStoreState.REFRESHING

    def _refresh_thread_entrypoint(self) -> None:
        try:
            self._rebuild_and_swap(failure_state=VectorStoreState.READY)
        except Exception as exc:
            print(f"[{self.name}] Background refresh failed: {exc}")
        finally:
            with self._lock:
                self._refresh_thread = None

    def _rebuild_and_swap(self, *, failure_state: VectorStoreState) -> None:
        try:
            new_index = self._build_index_from_provider()

            with self._lock:
                self._active_index = new_index
                self._state = VectorStoreState.READY

        except Exception:
            with self._lock:
                self._state = failure_state
            raise

    def _build_index_from_provider(self) -> FAISS:
        sources = self.provider.list_sources()

        docs: list[Document] = []
        ids: list[str] = []

        for source in tqdm(sources):
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

        print(
            f"[{self.name}] Building FAISS index with "
            f"{type(self.embeddings).__name__}: {self.embeddings}"
        )

        return FAISS.from_documents(docs, self.embeddings, ids=ids)

    def _daily_refresh_loop(self, hour: int, minute: int) -> None:
        try:
            while not self._daily_refresh_stop_event.is_set():
                wait_seconds = self._seconds_until_next_refresh(
                    hour=hour,
                    minute=minute,
                )

                print(
                    f"[{self.name}] Next scheduled refresh in "
                    f"{wait_seconds / 3600:.2f} hours"
                )

                if self._daily_refresh_stop_event.wait(timeout=wait_seconds):
                    break

                print(f"[{self.name}] Running scheduled refresh...")
                try:
                    self.refresh()
                    print(f"[{self.name}] Scheduled refresh completed")
                except Exception as exc:
                    print(f"[{self.name}] Scheduled refresh failed: {exc}")

        finally:
            print(f"[{self.name}] Daily refresh loop stopped")
            with self._lock:
                self._daily_refresh_thread = None

    @staticmethod
    def _seconds_until_next_refresh(hour: int, minute: int) -> float:
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if now >= target:
            target = target + timedelta(days=1)

        return (target - now).total_seconds()


if __name__ == "__main__":
    import time

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

    def main() -> None:
        data_dir = ensure_test_data()

        simple_test = ProviderSpec(
            type="filesystem",
            args={
                "path": str(data_dir),
                "glob": "*.txt",
            },
        )

        spec = VectorStoreSpec(
            name="test_store",
            provider=simple_test,
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
        print("Background refresh running:", store.is_background_refresh_running)
        print("Daily refresh running:", store.is_daily_refresh_running)

        try:
            store.similarity_search("test")
        except RuntimeError as exc:
            print("Expected failure before initialize:", exc)

        store.initialize()

        print("State after initialize:", store.state)
        print("Ready:", store.is_ready)

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

        print("\nStarting daily refresh loop...")
        store.start_daily_refresh_loop(hour=4, minute=30)
        print("Daily refresh running:", store.is_daily_refresh_running)

        print("\nRunning blocking refresh...")
        store.refresh()
        print("State after blocking refresh:", store.state)

        print("\nRunning background refresh...")
        refresh_thread = store.start_refresh()

        print("State during background refresh:", store.state)
        print("Background refresh running:", store.is_background_refresh_running)

        refresh_thread.join()

        print("State after background refresh:", store.state)
        print("Background refresh running:", store.is_background_refresh_running)

        try:
            time.sleep(5)
        finally:
            print("\nStopping daily refresh loop...")
            store.stop_daily_refresh_loop(timeout=5)
            print("Daily refresh running:", store.is_daily_refresh_running)

    main()