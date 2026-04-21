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
from tqdm import tqdm

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

from ruter_chatbot.logger import get_logger
from ruter_chatbot.stores.providers.base_provider import BaseProvider
from ruter_chatbot.stores.smart_chunker import SmartChunker
from ruter_chatbot.types.iac.embed_spec import EmbedSpec
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.types.keyed import Keyed
from ruter_chatbot.types.source import Source
from ruter_chatbot.types.spec_based import SpecBased
from ruter_chatbot.utility.aws import bedrock_runtime

logger = get_logger(__name__)


class VectorStoreState(str, Enum):
    INITIALIZING = "initializing"
    READY = "ready"
    REFRESHING = "refreshing"
    FAILED = "failed"


class VectorStoreRuntime(SpecBased[VectorStoreSpec], Keyed):
    """
    Thread-based runtime service for document retrieval + FAISS index lifecycle.
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
        embed_spec: EmbedSpec,
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
            embed_spec=spec.embedder,
        )

    def to_spec(self) -> VectorStoreSpec:
        return VectorStoreSpec(
            key=self.key,
            provider=self.provider.to_spec(),
            embedder=self._embed_spec,
            chunker=self.chunker.to_spec(),
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

            client = bedrock_runtime(region_name)

            return BedrockEmbeddings(
                client=client,
                model_id=model_id,
                **embed_args,
            )

        raise ValueError(f"Unsupported embedder type: {embed_type}")

    @property
    def embeddings(self) -> Embeddings:
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
        with self._lock:
            if self._active_index is not None:
                return
            self._state = VectorStoreState.INITIALIZING

        sources = self.provider.list_sources()
        if self._has_compatible_cached_index(sources):
            cached_index = self._load_cached_index()
            if cached_index is not None:
                with self._lock:
                    self._active_index = cached_index
                    self._state = VectorStoreState.READY
                return

        self._rebuild_and_swap(
            failure_state=VectorStoreState.FAILED,
            sources=sources,
        )

    def refresh(self) -> None:
        self._prepare_refresh()
        sources = self.provider.list_sources()
        self._rebuild_and_swap(
            failure_state=VectorStoreState.READY,
            sources=sources,
        )

    def clear_cache(self) -> None:
        with self._lock:
            self._active_index = None
            self._state = VectorStoreState.INITIALIZING

        shutil.rmtree(self._cache_dir, ignore_errors=True)

    def start_refresh(self) -> threading.Thread:
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
            sources = self.provider.list_sources()
            self._rebuild_and_swap(
                failure_state=VectorStoreState.READY,
                sources=sources,
            )
        except Exception as exc:
            logger.info(f"[{self.key}] Background refresh failed: {exc}")
        finally:
            with self._lock:
                self._refresh_thread = None

    def _rebuild_and_swap(
        self,
        *,
        failure_state: VectorStoreState,
        sources: list[Source],
    ) -> None:
        try:
            new_index, embedding_cache = self._build_index_from_provider(sources)
            self._save_cached_index(new_index, sources, embedding_cache)

            with self._lock:
                self._active_index = new_index
                self._state = VectorStoreState.READY

        except Exception:
            with self._lock:
                self._state = failure_state
            raise

    def _build_index_from_provider(
        self,
        sources: list[Source],
    ) -> tuple[FAISS, dict[str, dict[str, Any]]]:
        text_embedding_pairs: list[tuple[str, list[float]]] = []
        metadatas: list[dict[str, Any]] = []
        ids: list[str] = []
        embedding_cache = self._load_embedding_cache()
        next_embedding_cache: dict[str, dict[str, Any]] = {}
        chunk_records: list[dict[str, Any]] = []

        for source in tqdm(sources):
            source_docs: list[Document] = self.provider.get_docs_from_source(source)

            chunk_counter = 0
            for source_doc in source_docs:
                chunked_docs = self.chunker.split_documents(source_doc)

                for chunk_doc in chunked_docs:
                    metadata = dict(chunk_doc.metadata)
                    doc_id = f"{source.location}#chunk-{chunk_counter}"

                    metadata["doc_id"] = doc_id
                    chunk_doc.metadata = metadata

                    chunk_fingerprint = self._stable_hash(
                        {"text": chunk_doc.page_content}
                    )
                    chunk_records.append(
                        {
                            "chunk_id": doc_id,
                            "chunk_text": chunk_doc.page_content,
                            "chunk_metadata": metadata,
                            "chunk_fingerprint": chunk_fingerprint,
                        }
                    )

                    chunk_counter += 1

        embeddings_by_chunk_id = self._resolve_chunk_embeddings(
            chunk_records=chunk_records,
            embedding_cache=embedding_cache,
            next_embedding_cache=next_embedding_cache,
        )

        for chunk_record in chunk_records:
            chunk_id = chunk_record["chunk_id"]
            chunk_text = chunk_record["chunk_text"]
            chunk_metadata = chunk_record["chunk_metadata"]

            text_embedding_pairs.append((chunk_text, embeddings_by_chunk_id[chunk_id]))
            metadatas.append(chunk_metadata)
            ids.append(chunk_id)

        index = self._build_faiss_index(text_embedding_pairs, metadatas, ids)
        return index, next_embedding_cache

    def _build_faiss_index(
        self,
        text_embedding_pairs: list[tuple[str, list[float]]],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> FAISS:
        if not text_embedding_pairs:
            raise ValueError(
                f"VectorStore '{self.key}' could not build index: no documents found"
            )

        logger.info(
            f"[{self.key}] Building FAISS index from cached/new embeddings "
            f"with {type(self.embeddings).__name__}: {self.embeddings}"
        )

        return FAISS.from_embeddings(
            text_embedding_pairs,
            self.embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    def _resolve_cache_dir(self) -> Path:
        return Path(self.CACHE_ROOT) / self.key

    def _cache_manifest_path(self) -> Path:
        return self._cache_dir / "manifest.json"

    def _embedding_cache_path(self) -> Path:
        return self._cache_dir / "chunk_embeddings.json"

    def _stable_hash(self, payload: dict | list[dict]) -> str:
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def _config_fingerprint(self) -> str:
        payload = {
            "provider": self.provider.to_spec().model_dump(mode="json"),
            "embedder": self._embed_spec.model_dump(mode="json"),
            "chunker": self.chunker.to_spec().model_dump(mode="json"),
        }
        return self._stable_hash(payload)

    def _source_fingerprint(self, sources: list[Source]) -> str:
        payload = [
            {
                "location": source.location,
                "type": source.type,
                "meta": source.meta,
            }
            for source in sorted(sources, key=lambda source: source.location)
        ]
        return self._stable_hash(payload)

    def _cache_fingerprint(self, sources: list[Source]) -> str:
        payload = {
            "config": self._config_fingerprint(),
            "sources": self._source_fingerprint(sources),
        }
        return self._stable_hash(payload)

    def _cache_manifest(self, sources: list[Source]) -> dict[str, Any]:
        return {
            "store": self.key,
            "fingerprint": self._cache_fingerprint(sources),
        }

    def _load_embedding_cache(self) -> dict[str, dict[str, Any]]:
        path = self._embedding_cache_path()
        if not path.exists():
            return {}

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("[%s] Failed to read embedding cache: %s", self.key, exc)
            return {}

        if not isinstance(payload, dict):
            logger.warning("[%s] Ignoring malformed embedding cache", self.key)
            return {}

        return payload

    def _resolve_chunk_embeddings(
        self,
        *,
        chunk_records: list[dict[str, Any]],
        embedding_cache: dict[str, dict[str, Any]],
        next_embedding_cache: dict[str, dict[str, Any]],
    ) -> dict[str, list[float]]:
        embeddings_by_chunk_id: dict[str, list[float]] = {}
        missing_chunk_records: list[dict[str, Any]] = []

        for chunk_record in chunk_records:
            chunk_id = chunk_record["chunk_id"]
            chunk_text = chunk_record["chunk_text"]
            chunk_metadata = chunk_record["chunk_metadata"]
            chunk_fingerprint = chunk_record["chunk_fingerprint"]
            cached = embedding_cache.get(chunk_id)

            if cached and cached.get("chunk_fingerprint") == chunk_fingerprint:
                embedding = cached["embedding"]
                embeddings_by_chunk_id[chunk_id] = embedding
                next_embedding_cache[chunk_id] = {
                    "chunk_fingerprint": chunk_fingerprint,
                    "text": chunk_text,
                    "metadata": chunk_metadata,
                    "embedding": embedding,
                }
                continue

            missing_chunk_records.append(chunk_record)

        if missing_chunk_records:
            missing_texts = [
                chunk_record["chunk_text"] for chunk_record in missing_chunk_records
            ]
            missing_embeddings = self.embeddings.embed_documents(missing_texts)

            for chunk_record, embedding in zip(
                missing_chunk_records,
                missing_embeddings,
                strict=True,
            ):
                chunk_id = chunk_record["chunk_id"]
                embeddings_by_chunk_id[chunk_id] = embedding
                next_embedding_cache[chunk_id] = {
                    "chunk_fingerprint": chunk_record["chunk_fingerprint"],
                    "text": chunk_record["chunk_text"],
                    "metadata": chunk_record["chunk_metadata"],
                    "embedding": embedding,
                }

        return embeddings_by_chunk_id

    def _read_cache_manifest(self) -> dict[str, Any] | None:
        manifest_path = self._cache_manifest_path()
        if not manifest_path.exists():
            return None

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("[%s] Failed to read cache manifest: %s", self.key, exc)
            return None

        if not isinstance(manifest, dict):
            logger.warning("[%s] Ignoring malformed cache manifest", self.key)
            return None

        return manifest

    def _has_compatible_cached_index(self, sources: list[Source]) -> bool:
        manifest = self._read_cache_manifest()
        if manifest is None:
            return False

        if manifest.get("fingerprint") != self._cache_fingerprint(sources):
            logger.info(
                "[%s] Ignoring stale FAISS cache due to source/config mismatch",
                self.key,
            )
            return False

        return True

    def _load_cached_index(self) -> FAISS | None:
        if self._read_cache_manifest() is None:
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

    def _save_cached_index(
        self,
        index: FAISS,
        sources: list[Source],
        embedding_cache: dict[str, dict[str, Any]],
    ) -> None:
        temp_dir = self._cache_dir.parent / f"{self._cache_dir.name}.tmp"
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            index.save_local(str(temp_dir))
            self._cache_dir.parent.mkdir(parents=True, exist_ok=True)
            (temp_dir / "manifest.json").write_text(
                json.dumps(self._cache_manifest(sources), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            (temp_dir / "chunk_embeddings.json").write_text(
                json.dumps(embedding_cache, indent=2, sort_keys=True),
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
