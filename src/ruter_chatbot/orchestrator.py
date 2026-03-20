from __future__ import annotations

from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from ruter_chatbot.graph.node_registry import NodeRegistry
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
from ruter_chatbot.types.iac.app_spec import AppSpec
from ruter_chatbot.types.iac.edge_spec import RouterEdgeSpec, SimpleEdgeSpec
from ruter_chatbot.types.iac.graph_spec import GraphSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec

import logging

logging.getLogger("langchain_aws").setLevel(logging.WARNING)


class Orchestrator:
    def __init__(self, spec: AppSpec) -> None:
        self.spec = spec

        self.models = ModelRegistry()
        self.pipelines = PipelineRegistry(self.models)
        self.vector_stores = VectorStoreRegistry()
        self.prompts: dict[str, PromptSpec] = {}

        self.nodes = NodeRegistry(
            pipelines=self.pipelines,
            vector_stores=self.vector_stores,
            prompts=self.prompts,
        )

        self._load_specs()
        self.build_graph(self.spec.graph)

    def _load_specs(self) -> None:
        for model_spec in self.spec.models.values():
            self.models.from_spec(model_spec)

        for pipeline_spec in self.spec.pipelines.values():
            self.pipelines.from_spec(pipeline_spec)

        for prompt_spec in self.spec.prompts.values():
            self.prompts[prompt_spec.key] = prompt_spec

        for vector_store_spec in self.spec.vector_stores.values():
            self.vector_stores.from_spec(vector_store_spec)

        for node_spec in self.spec.graph.nodes:
            self.nodes.from_spec(node_spec)

    def list_vector_stores(self) -> VectorStoreListResponse:
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
            self.vector_stores.initialize_all()
            return

        missing = [key for key in store_keys if key not in self.spec.vector_stores]
        if missing:
            raise KeyError(f"Unknown vector store(s): {', '.join(missing)}")

        for store_key in store_keys:
            self.vector_stores.initialize(store_key)

    def build_graph(self, graph_spec: GraphSpec | dict[str, Any]):
        if not isinstance(graph_spec, GraphSpec):
            graph_spec = GraphSpec.model_validate(graph_spec)

        if graph_spec.state_key not in state_registry:
            raise KeyError(f"Unknown state_key: {graph_spec.state_key}")

        state_type = state_registry[graph_spec.state_key]
        builder = StateGraph(state_type)

        for node_spec in graph_spec.nodes:
            builder.add_node(node_spec.name, self.nodes.get(node_spec.name))

        edge_sources: set[str] = set()
        edge_targets: set[str] = set()
        all_nodes = {node_spec.name for node_spec in graph_spec.nodes}

        for edge in graph_spec.edges:
            edge_sources.add(edge.source)

            if isinstance(edge, SimpleEdgeSpec):
                builder.add_edge(edge.source, edge.target)
                edge_targets.add(edge.target)
                continue

            if isinstance(edge, RouterEdgeSpec):
                path_map = dict(edge.routes)
                if edge.default_target:
                    path_map["__default__"] = edge.default_target

                edge_targets.update(edge.routes.values())
                if edge.default_target:
                    edge_targets.add(edge.default_target)

                def _route_with_default(
                    state: Any,
                    *,
                    _route_field=edge.state_route_field,
                    _path_map=path_map,
                    _default=edge.default_target,
                ) -> str | None:
                    if isinstance(state, dict):
                        result = state.get(_route_field)
                    else:
                        result = getattr(state, _route_field, None)

                    if result in _path_map:
                        return result
                    if _default:
                        return "__default__"
                    return result

                builder.add_conditional_edges(
                    edge.source,
                    _route_with_default,
                    path_map=path_map,
                )
                continue

            raise TypeError(f"Unsupported edge type: {type(edge)!r}")

        entry_nodes = all_nodes - edge_targets
        if not entry_nodes and graph_spec.nodes:
            entry_nodes = {graph_spec.nodes[0].name}

        for entry in entry_nodes:
            builder.add_edge(START, entry)

        leaf_nodes = all_nodes - edge_sources
        for leaf in leaf_nodes:
            builder.add_edge(leaf, END)

        compile_kwargs: dict[str, Any] = {}
        if graph_spec.compile_args.use_memory:
            compile_kwargs["checkpointer"] = MemorySaver()

        self.graph = builder.compile(**compile_kwargs)
        self.spec.graph = graph_spec
        return self.graph


    def _extract_answer_from_state(self, state: AskState | dict[str, Any]) -> str:
        fb = "I couldn't answer the question."
        message = fb

        answer = state.get("answer") if isinstance(state, dict) else getattr(state, "answer", None)
        if not answer:
            messages = state.get("messages") if isinstance(state, dict) else getattr(state, "messages", None)
            if not messages:
                return message
            
            message = next(
                (m for m in reversed(messages)
                if isinstance(m, AIMessage)),
                messages[-1]
            )

        answer = answer or message
        if isinstance(answer, str):
            return answer
        
        return getattr(answer, 'text', fb) # fb is not needed here except to stop linter complaints.
    
    def ask(
        self,
        question: str,
        conversation_id: str | None = None,
        debug: bool = False,
    ) -> AskResponse:
        use_memory = self.spec.graph.compile_args.use_memory
        resolved_conversation_id = conversation_id or str(uuid4()) if use_memory else None

        input_state = {"question": question}
        config = None

        if resolved_conversation_id:
            config = {
                "configurable": {
                    "thread_id": resolved_conversation_id
                }
            }

        out = self.graph.invoke(input_state, config=config)
        state_type = state_registry[self.spec.graph.state_key]

        if issubclass(state_type, BaseModel):
            result = out if isinstance(out, state_type) else state_type.model_validate(out)
        else:
            result = out

        return AskResponse(
            answer=self._extract_answer_from_state(result),
            conversation_id=resolved_conversation_id if use_memory else None,
            state=result if debug else None,
        )