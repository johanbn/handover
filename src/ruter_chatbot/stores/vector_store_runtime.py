import hashlib
import json
import os
import shutil
import subprocess
import threading
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import boto3
from tqdm import tqdm

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

from ruter_chatbot.stores.providers.base_provider import BaseProvider
from ruter_chatbot.stores.smart_chunker import SmartChunker
from ruter_chatbot.types.iac.embed_spec import EmbedSpec
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.types.keyed import Keyed
from ruter_chatbot.types.spec_based import SpecBased
from ruter_chatbot.logger import get_logger
logger = get_logger(__name__)


class VectorStoreState(str, Enum):
    INITIALIZING = "initializing"
    READY = "ready"
    REFRESHING = "refreshing"
    FAILED = "failed"


class VectorStoreRuntime(SpecBased[VectorStoreSpec], Keyed):
    """
    Thread-based runtime service for document retrieval + FAISS index lifecycle.

    Lifecycle
    ---------
    - from_spec() creates the store
    - initialize() loads a cached FAISS snapshot if available, otherwise builds
      the first index (blocking)
    - refresh() rebuilds and swaps in a new index (blocking)
    - start_refresh() rebuilds and swaps in a new index (background thread)
    - start_daily_refresh_loop() runs recurring background refresh
    - searches always use the current active index
    - active index is only swapped when the new one is fully built
    """
    spec_class = VectorStoreSpec
    CACHE_ENV_VAR = "VECTOR_STORE_CACHE_DIR"
    DEFAULT_CACHE_ROOT = ".local/vector_store_cache"
    CACHE_ROOT = os.environ.get(CACHE_ENV_VAR) or DEFAULT_CACHE_ROOT

    def __init__(
        self,
        *,
        key: str,
        provider: BaseProvider,
        embeddings: Embeddings,
        chunker: SmartChunker,
        embed_spec: EmbedSpec # pragmatic addition for isomorphism
    ) -> None:
        self.key = key
        self.provider = provider
        self._embeddings = embeddings
        self.chunker = chunker
        self._embed_spec: EmbedSpec = embed_spec
        self._cache_dir = self._resolve_cache_dir()

        self._state: VectorStoreState = VectorStoreState.INITIALIZING
        self._active_index: FAISS | None = None

        self._lock = threading.RLock()

        self._refresh_thread: threading.Thread | None = None
        self._daily_refresh_thread: threading.Thread | None = None
        self._daily_refresh_stop_event = threading.Event()

    @classmethod
    def from_spec(cls, spec: "VectorStoreSpec") -> "VectorStoreRuntime":
        logger.info(
            f"Creating VectorStore "
            f"key={spec.key} "
            f"embedder_type={spec.embedder.type} "
            f"embedder_args={spec.embedder.args}"
        )

        provider = BaseProvider.from_spec(spec.provider)
        embeddings = cls._build_embeddings_from_spec(spec.embedder)
        chunker = SmartChunker.from_spec(spec.chunker)

        logger.info(
            f"[{spec.key}] Created embeddings instance: "
            f"{type(embeddings).__name__}"
        )

        return cls(
            key=spec.key,
            provider=provider,
            embeddings=embeddings,
            chunker=chunker,
            embed_spec=spec.embedder
        )

    def to_spec(self) -> VectorStoreSpec:
        return VectorStoreSpec(
            key=self.key,
            provider=self.provider.to_spec(),
            embedder=self._embed_spec,
            chunker=self.chunker.to_spec()
        )

    @staticmethod
    def _build_embeddings_from_spec(embed_spec: "EmbedSpec") -> Any:
        embed_type = embed_spec.type
        embed_args = dict(embed_spec.args)

        if embed_type == "ollama":
            try:
                from langchain_ollama import OllamaEmbeddings
            except ImportError:
                raise RuntimeError(
                    "Cannot load Ollama embedding: langchain-ollama is not installed.\n"
                    "This is intended in production.\n"
                    "Avoid using Ollama embeddings in production."
                ) from None
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
            try:
                from langchain_aws import BedrockEmbeddings
            except ImportError:
                raise RuntimeError(
                    "Cannot load Bedrock Embedding: langchain_aws is not installed."
                ) from None

            model_id = embed_args.pop("model_id", None)
            region_name = embed_args.pop(
                "region_name",
                os.environ.get('AWS_REGION')
            )

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
    def embeddings(self) -> Embeddings: # to prevent edits
        return self._embeddings

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
            raise RuntimeError(f"VectorStore '{self.key}' is not ready")

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
        Safe to call multiple times; only the first successful call loads or builds
        the index.
        """
        with self._lock:
            if self._active_index is not None:
                return
            self._state = VectorStoreState.INITIALIZING

        cached_index = self._load_cached_index()
        if cached_index is not None:
            with self._lock:
                self._active_index = cached_index
                self._state = VectorStoreState.READY
            return

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
            name=f"{self.key}-refresh",
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
                    f"VectorStore '{self.key}' daily refresh loop already running"
                )

            self._daily_refresh_stop_event.clear()

            thread = threading.Thread(
                target=self._daily_refresh_loop,
                kwargs={"hour": hour, "minute": minute},
                name=f"{self.key}-daily-refresh-loop",
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
                    f"VectorStore '{self.key}' cannot refresh before initialization"
                )

            if self._refresh_thread and self._refresh_thread.is_alive():
                raise RuntimeError(
                    f"VectorStore '{self.key}' refresh already running"
                )

            self._state = VectorStoreState.REFRESHING

    def _refresh_thread_entrypoint(self) -> None:
        try:
            self._rebuild_and_swap(failure_state=VectorStoreState.READY)
        except Exception as exc:
            logger.info(f"[{self.key}] Background refresh failed: {exc}")
        finally:
            with self._lock:
                self._refresh_thread = None

    def _rebuild_and_swap(self, *, failure_state: VectorStoreState) -> None:
        try:
            new_index = self._build_index_from_provider()
            self._save_cached_index(new_index)

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
                f"VectorStore '{self.key}' could not build index: no documents found"
            )

        logger.info(
            f"[{self.key}] Building FAISS index with "
            f"{type(self.embeddings).__name__}: {self.embeddings}"
        )

        return FAISS.from_documents(docs, self.embeddings, ids=ids)

    def _resolve_cache_dir(self) -> Path:
        return Path(self.CACHE_ROOT) / self.key

    def _cache_manifest_path(self) -> Path:
        return self._cache_dir / "manifest.json"

    def _cache_fingerprint(self) -> str:
        payload = {
            "provider": self.provider.to_spec().model_dump(mode="json"),
            "embedder": self._embed_spec.model_dump(mode="json"),
            "chunker": self.chunker.to_spec().model_dump(mode="json"),
        }
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def _cache_manifest(self) -> dict[str, Any]:
        return {
            "store": self.key,
            "fingerprint": self._cache_fingerprint(),
        }

    def _load_cached_index(self) -> FAISS | None:
        manifest_path = self._cache_manifest_path()
        if not manifest_path.exists():
            return None

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("[%s] Failed to read cache manifest: %s", self.key, exc)
            return None

        if manifest.get("fingerprint") != self._cache_fingerprint():
            logger.info("[%s] Ignoring stale FAISS cache due to spec mismatch", self.key)
            return None

        try:
            logger.info("[%s] Loading FAISS index from cache: %s", self.key, self._cache_dir)
            return FAISS.load_local(
                str(self._cache_dir),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception as exc:
            logger.warning("[%s] Failed to load FAISS cache: %s", self.key, exc)
            return None

    def _save_cached_index(self, index: FAISS) -> None:
        temp_dir = self._cache_dir.parent / f"{self._cache_dir.name}.tmp"
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            index.save_local(str(temp_dir))
            self._cache_dir.parent.mkdir(parents=True, exist_ok=True)
            (temp_dir / "manifest.json").write_text(
                json.dumps(self._cache_manifest(), indent=2, sort_keys=True),
                encoding="utf-8",
            )

            if self._cache_dir.exists():
                shutil.rmtree(self._cache_dir)

            temp_dir.replace(self._cache_dir)
            logger.info("[%s] Saved FAISS cache to %s", self.key, self._cache_dir)
        except Exception as exc:
            logger.warning("[%s] Failed to persist FAISS cache: %s", self.key, exc)
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _daily_refresh_loop(self, hour: int, minute: int) -> None:
        try:
            while not self._daily_refresh_stop_event.is_set():
                wait_seconds = self._seconds_until_next_refresh(
                    hour=hour,
                    minute=minute,
                )

                logger.info(
                    f"[{self.key}] Next scheduled refresh in "
                    f"{wait_seconds / 3600:.2f} hours"
                )

                if self._daily_refresh_stop_event.wait(timeout=wait_seconds):
                    break

                logger.info(f"[{self.key}] Running scheduled refresh...")
                try:
                    self.refresh()
                    logger.info(f"[{self.key}] Scheduled refresh completed")
                except Exception as exc:
                    logger.info(f"[{self.key}] Scheduled refresh failed: {exc}")

        finally:
            logger.info(f"[{self.key}] Daily refresh loop stopped")
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
            key="test_store",
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

        store = VectorStoreRuntime.from_spec(spec)

        logger.info("Initial state:", store.state)
        logger.info("Background refresh running:", store.is_background_refresh_running)
        logger.info("Daily refresh running:", store.is_daily_refresh_running)

        try:
            store.similarity_search("test")
        except RuntimeError as exc:
            logger.info("Expected failure before initialize:", exc)

        store.initialize()

        logger.info("State after initialize:", store.state)
        logger.info("Ready:", store.is_ready)

        results = store.similarity_search(
            "Hva handler dokumentene om?",
            k=3,
        )

        logger.info("\nSimilarity search results:")
        for result in results:
            logger.info("-", result.page_content[:100], "|", result.metadata)

        scored_results = store.similarity_search(
            "Hva handler dokumentene om?",
            k=3,
            with_score=True,
        )

        logger.info("\nSimilarity search results (with score):")
        for doc, score in scored_results:
            logger.info(f"- score={score:.4f} | {doc.page_content[:100]} | {doc.metadata}")

        mmr_results = store.max_marginal_relevance_search(
            "Hva handler dokumentene om?",
            k=3,
            fetch_k=10,
            lambda_mult=0.5,
        )

        logger.info("\nMMR search results:")
        for result in mmr_results:
            logger.info("-", result.page_content[:100], "|", result.metadata)

        logger.info("\nStarting daily refresh loop...")
        store.start_daily_refresh_loop(hour=4, minute=30)
        logger.info("Daily refresh running:", store.is_daily_refresh_running)

        logger.info("\nRunning blocking refresh...")
        store.refresh()
        logger.info("State after blocking refresh:", store.state)

        logger.info("\nRunning background refresh...")
        refresh_thread = store.start_refresh()

        logger.info("State during background refresh:", store.state)
        logger.info("Background refresh running:", store.is_background_refresh_running)

        refresh_thread.join()

        logger.info("State after background refresh:", store.state)
        logger.info("Background refresh running:", store.is_background_refresh_running)

        try:
            time.sleep(5)
        finally:
            logger.info("\nStopping daily refresh loop...")
            store.stop_daily_refresh_loop(timeout=5)
            logger.info("Daily refresh running:", store.is_daily_refresh_running)

    main()
