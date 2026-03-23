from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage
from pydantic import BaseModel

from ruter_chatbot.graph.graph_builder import GraphBuilder
from ruter_chatbot.graph.node_builder import NodeBuilder
from ruter_chatbot.llm.model_registry import ModelRegistry
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.specs.state import state_registry
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.app.ask import AskResponse, AskState
from ruter_chatbot.types.app.vector_store import (
    MmrSearchRequest,
    SimilaritySearchRequest,
    VectorStoreInfo,
    VectorStoreListResponse,
    VectorStoreSearchHit,
    VectorStoreSearchResponse,
)
from ruter_chatbot.types.iac.app_spec import OrchestratorSpec
from ruter_chatbot.types.iac.graph_spec import GraphSpec
from ruter_chatbot.types.iac.model_spec import ModelSpec
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec, RetrieverNodeSpec
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.graph.graph_builder import GraphBuilder

logging.getLogger("langchain_aws").setLevel(logging.WARNING)


class Orchestrator:
    def __init__(
        self,
        *,
        models: dict[str, ModelSpec] | None = None,
        pipelines: dict[str, PipelineSpec] | None = None,
        prompts: dict[str, PromptSpec] | None = None,
        vector_stores: dict[str, VectorStoreSpec] | None = None,
        graph: GraphSpec | dict[str, Any] | None = None,
    ) -> None:
        self.model_specs: dict[str, ModelSpec] = models or {}
        self.pipeline_specs: dict[str, PipelineSpec] = pipelines or {}
        self.prompt_specs: dict[str, PromptSpec] = prompts or {}
        self.vector_store_specs: dict[str, VectorStoreSpec] = vector_stores or {}
        self.graph_spec: GraphSpec | None = (
            GraphSpec.model_validate(graph)
            if graph is not None and not isinstance(graph, GraphSpec)
            else graph
        )

        self.models: ModelRegistry = ModelRegistry()
        self.pipelines: PipelineRegistry = PipelineRegistry(self.models)
        self.vector_stores: VectorStoreRegistry = VectorStoreRegistry()
        self.prompts: dict[str, PromptSpec] = {}

        self.graph = None

        self._model_signatures: dict[str, str] = {}
        self._pipeline_signatures: dict[str, str] = {}
        self._prompt_signatures: dict[str, str] = {}
        self._vector_store_signatures: dict[str, str] = {}
        self._used_spec_signature: str | None = None

    @classmethod
    def from_spec(cls, spec: OrchestratorSpec) -> "Orchestrator":
        return cls(
            models=spec.models,
            pipelines=spec.pipelines,
            prompts=spec.prompts,
            vector_stores=spec.vector_stores,
            graph=spec.graph,
        )

    def to_declared_spec(self) -> OrchestratorSpec:
        if self.graph_spec is None:
            raise ValueError("Orchestrator has no declared graph spec.")

        return OrchestratorSpec(
            models=self.model_specs,
            pipelines=self.pipeline_specs,
            prompts=self.prompt_specs,
            vector_stores=self.vector_store_specs,
            graph=self.graph_spec,
        )

    @property
    def spec(self) -> OrchestratorSpec:
        return self.to_declared_spec()

    def _spec_signature(self, spec: Any) -> str:
        if hasattr(spec, "model_dump"):
            payload = spec.model_dump(mode="json", exclude_none=True)
        elif isinstance(spec, dict):
            payload = spec
        else:
            payload = str(spec)

        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _resolve_used_spec(self) -> OrchestratorSpec:
        if self.graph_spec is None:
            raise ValueError("Orchestrator has no declared graph spec.")

        used_models: set[str] = set()
        used_pipelines: set[str] = set()
        used_prompts: set[str] = set()
        used_vector_stores: set[str] = set()

        def use_model(key: str) -> None:
            if key not in self.model_specs:
                raise KeyError(f"Unknown model: {key}")
            used_models.add(key)

        def use_prompt(key: str) -> None:
            if key not in self.prompt_specs:
                raise KeyError(f"Unknown prompt: {key}")
            used_prompts.add(key)

        def use_vector_store(key: str) -> None:
            if key not in self.vector_store_specs:
                raise KeyError(f"Unknown vector store: {key}")
            if key in used_vector_stores:
                return

            used_vector_stores.add(key)
            spec = self.vector_store_specs[key]

            embedding_model_key = getattr(spec, "embedding_model_key", None)
            if embedding_model_key:
                use_model(embedding_model_key)

        def use_pipeline(key: str) -> None:
            if key not in self.pipeline_specs:
                raise KeyError(f"Unknown pipeline: {key}")
            if key in used_pipelines:
                return

            used_pipelines.add(key)
            spec = self.pipeline_specs[key]

            model_key = getattr(spec, "model_key", None)
            if model_key:
                use_model(model_key)

            prompt_key = getattr(spec, "prompt_key", None)
            if prompt_key:
                use_prompt(prompt_key)

            vector_store_key = getattr(spec, "vector_store_key", None)
            if vector_store_key:
                use_vector_store(vector_store_key)

        for node in self.graph_spec.nodes:
            if isinstance(node, LLMNodeSpec):
                use_pipeline(node.pipeline_key)
                use_prompt(node.prompt_key)
            elif isinstance(node, RetrieverNodeSpec):
                use_vector_store(node.store_key)

        return OrchestratorSpec(
            models={k: self.model_specs[k] for k in used_models},
            pipelines={k: self.pipeline_specs[k] for k in used_pipelines},
            prompts={k: self.prompt_specs[k] for k in used_prompts},
            vector_stores={k: self.vector_store_specs[k] for k in used_vector_stores},
            graph=self.graph_spec,
        )

    def to_used_spec(self) -> OrchestratorSpec:
        return self._resolve_used_spec()

    def _used_spec_digest(self, spec: OrchestratorSpec) -> str:
        payload = {
            "models": {
                k: v.model_dump(mode="json", exclude_none=True)
                for k, v in sorted(spec.models.items())
            },
            "pipelines": {
                k: v.model_dump(mode="json", exclude_none=True)
                for k, v in sorted(spec.pipelines.items())
            },
            "prompts": {
                k: v.model_dump(mode="json", exclude_none=True)
                for k, v in sorted(spec.prompts.items())
            },
            "vector_stores": {
                k: v.model_dump(mode="json", exclude_none=True)
                for k, v in sorted(spec.vector_stores.items())
            },
            "graph": spec.graph.model_dump(mode="json", exclude_none=True),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _remove_model_runtime(self, key: str) -> None:
        self.models.models.pop(key, None)
        self._model_signatures.pop(key, None)

    def _remove_pipeline_runtime(self, key: str) -> None:
        self.pipelines.pipelines.pop(key, None)
        self._pipeline_signatures.pop(key, None)

    def _remove_prompt_runtime(self, key: str) -> None:
        self.prompts.pop(key, None)
        self._prompt_signatures.pop(key, None)

    def _remove_vector_store_runtime(self, key: str) -> None:
        self.vector_stores.vector_stores.pop(key, None)
        self._vector_store_signatures.pop(key, None)

    def _ensure_model(self, key: str, spec: ModelSpec) -> None:
        signature = self._spec_signature(spec)
        current_signature = self._model_signatures.get(key)

        if key in self.models.models and current_signature == signature:
            return

        if key in self.models.models:
            self._remove_model_runtime(key)

        self.models.from_spec(spec)
        self._model_signatures[key] = signature

    def _ensure_prompt(self, key: str, spec: PromptSpec) -> None:
        signature = self._spec_signature(spec)
        current_signature = self._prompt_signatures.get(key)

        if key in self.prompts and current_signature == signature:
            return

        self.prompts[key] = spec
        self._prompt_signatures[key] = signature

    def _ensure_vector_store(self, key: str, spec: VectorStoreSpec) -> None:
        signature = self._spec_signature(spec)
        current_signature = self._vector_store_signatures.get(key)

        if key in self.vector_stores.vector_stores and current_signature == signature:
            return

        if key in self.vector_stores.vector_stores:
            self._remove_vector_store_runtime(key)

        self.vector_stores.from_spec(spec)
        self._vector_store_signatures[key] = signature

    def _ensure_pipeline(self, key: str, spec: PipelineSpec) -> None:
        signature = self._spec_signature(spec)
        current_signature = self._pipeline_signatures.get(key)

        if key in self.pipelines.pipelines and current_signature == signature:
            return

        if key in self.pipelines.pipelines:
            self._remove_pipeline_runtime(key)

        self.pipelines.from_spec(spec)
        self._pipeline_signatures[key] = signature

    def _prune_unused_runtime(self, used_spec: OrchestratorSpec) -> None:
        used_model_keys = set(used_spec.models.keys())
        used_pipeline_keys = set(used_spec.pipelines.keys())
        used_prompt_keys = set(used_spec.prompts.keys())
        used_vector_store_keys = set(used_spec.vector_stores.keys())

        for key in list(self.models.models.keys()):
            if key not in used_model_keys:
                self._remove_model_runtime(key)

        for key in list(self.pipelines.pipelines.keys()):
            if key not in used_pipeline_keys:
                self._remove_pipeline_runtime(key)

        for key in list(self.prompts.keys()):
            if key not in used_prompt_keys:
                self._remove_prompt_runtime(key)

        for key in list(self.vector_stores.vector_stores.keys()):
            if key not in used_vector_store_keys:
                self._remove_vector_store_runtime(key)

    def rebuild(self) -> None:
        if self.graph_spec is None:
            raise ValueError("Cannot rebuild without graph spec.")

        used_spec = self._resolve_used_spec()
        used_signature = self._used_spec_digest(used_spec)

        for key, spec in used_spec.models.items():
            self._ensure_model(key, spec)

        for key, spec in used_spec.prompts.items():
            self._ensure_prompt(key, spec)

        for key, spec in used_spec.vector_stores.items():
            self._ensure_vector_store(key, spec)

        for key, spec in used_spec.pipelines.items():
            self._ensure_pipeline(key, spec)

        self._prune_unused_runtime(used_spec)

        if self.graph is not None and self._used_spec_signature == used_signature:
            return

        node_builder = NodeBuilder(
            pipelines=self.pipelines,
            vector_stores=self.vector_stores,
            prompts=self.prompts,
        )
        graph_builder = GraphBuilder(node_builder)
        self.graph = graph_builder.build(used_spec.graph)
        self._used_spec_signature = used_signature
        return self.graph

    def build_graph(
        self,
        graph_spec: GraphSpec | dict[str, Any] | None = None,
    ):
        if graph_spec is not None:
            self.graph_spec = (
                GraphSpec.model_validate(graph_spec)
                if not isinstance(graph_spec, GraphSpec)
                else graph_spec
            )

        if self.graph is None:
            self.rebuild()
            return self.graph

        used_spec = self._resolve_used_spec()
        used_signature = self._used_spec_digest(used_spec)

        if self._used_spec_signature != used_signature:
            self.rebuild()

        return self.graph

    def list_vector_stores(self) -> VectorStoreListResponse:
        for key, spec in self.vector_store_specs.items():
            self._ensure_vector_store(key, spec)

        return VectorStoreListResponse(
            stores=[
                VectorStoreInfo(
                    name=name,
                    state=store.state.value,
                )
                for name, store in self.vector_stores.vector_stores.items()
            ]
        )

    def _build_hits(self, docs: list[Any]) -> list[VectorStoreSearchHit]:
        return [
            VectorStoreSearchHit(
                page_content=doc.page_content,
                metadata=dict(doc.metadata),
            )
            for doc in docs
        ]

    def _build_scored_hits(
        self,
        docs_with_scores: list[tuple[Any, float]],
    ) -> list[VectorStoreSearchHit]:
        return [
            VectorStoreSearchHit(
                page_content=doc.page_content,
                metadata=dict(doc.metadata),
                score=float(score),
            )
            for doc, score in docs_with_scores
        ]

    def _search_response(
        self,
        *,
        store_name: str,
        query: str,
        k: int,
        hits: list[VectorStoreSearchHit],
    ) -> VectorStoreSearchResponse:
        return VectorStoreSearchResponse(
            store_name=store_name,
            query=query,
            k=k,
            hits=hits,
        )

    def search_vector_store_similarity(
        self,
        request: SimilaritySearchRequest,
    ) -> VectorStoreSearchResponse:
        if request.store_name not in self.vector_store_specs:
            raise KeyError(f"Unknown vector store: {request.store_name}")

        self._ensure_vector_store(
            request.store_name,
            self.vector_store_specs[request.store_name],
        )

        store = self.vector_stores.get(request.store_name)

        results = store.similarity_search(
            request.query,
            k=request.k,
            with_score=request.with_score,
        )

        hits = (
            self._build_scored_hits(results)
            if request.with_score
            else self._build_hits(results)
        )

        return self._search_response(
            store_name=request.store_name,
            query=request.query,
            k=request.k,
            hits=hits,
        )

    def search_vector_store_mmr(
        self,
        request: MmrSearchRequest,
    ) -> VectorStoreSearchResponse:
        if request.store_name not in self.vector_store_specs:
            raise KeyError(f"Unknown vector store: {request.store_name}")

        self._ensure_vector_store(
            request.store_name,
            self.vector_store_specs[request.store_name],
        )

        store = self.vector_stores.get(request.store_name)

        results = store.max_marginal_relevance_search(
            request.query,
            k=request.k,
            fetch_k=request.fetch_k,
            lambda_mult=request.lambda_mult,
        )

        return self._search_response(
            store_name=request.store_name,
            query=request.query,
            k=request.k,
            hits=self._build_hits(results),
        )

    def initialize(self, *store_keys: str) -> None:
        if not store_keys:
            store_keys = tuple(self.vector_store_specs.keys())

        missing = [key for key in store_keys if key not in self.vector_store_specs]
        if missing:
            raise KeyError(f"Unknown vector store(s): {', '.join(missing)}")

        for key in store_keys:
            self._ensure_vector_store(key, self.vector_store_specs[key])

        for key in store_keys:
            self.vector_stores.initialize(key)

    def _extract_answer_from_state(self, state: AskState | dict[str, Any]) -> str:
        fallback = "I couldn't answer the question."
        message = None

        answer = state.get("answer") if isinstance(state, dict) else getattr(state, "answer", None)
        if not answer:
            messages = state.get("messages") if isinstance(state, dict) else getattr(state, "messages", None)
            if not messages:
                return fallback

            message = next(
                (m for m in reversed(messages) if isinstance(m, AIMessage)),
                messages[-1],
            )

        answer = answer or message or fallback
        if isinstance(answer, str):
            return answer

        return getattr(answer, "text", fallback)

    def ask(
        self,
        question: str,
        conversation_id: str | None = None,
        debug: bool = False,
    ) -> AskResponse:
        graph = self.build_graph()

        if graph is None:
            raise ValueError("Graph is not available after rebuild.")

        if self.graph_spec is None:
            raise ValueError("Graph spec is missing.")

        use_memory = self.graph_spec.compile_args.use_memory
        resolved_conversation_id = conversation_id or str(uuid4()) if use_memory else None

        input_state = {"question": question}
        config = None

        if resolved_conversation_id:
            config = {
                "configurable": {
                    "thread_id": resolved_conversation_id,
                }
            }

        out = graph.invoke(input_state, config=config)
        state_type = state_registry[self.graph_spec.state_key]

        if issubclass(state_type, BaseModel):
            result = out if isinstance(out, state_type) else state_type.model_validate(out)
        else:
            result = out

        return AskResponse(
            answer=self._extract_answer_from_state(result),
            conversation_id=resolved_conversation_id if use_memory else None,
            state=result if debug else None,
        )