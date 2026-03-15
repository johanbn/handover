from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ruter_chatbot.graph.node_registry import NodeRegistry
from ruter_chatbot.llm.model_registry import ModelRegistry
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.specs.state import state_registry
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.iac.app_spec import AppSpec
from ruter_chatbot.types.iac.edge_spec import RouterEdgeSpec, SimpleEdgeSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.state_spec import RagState


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
        self.graph = self.build_graph(self.spec.graph)

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

    async def initialize(self, *store_keys: str) -> None:
        if not store_keys:
            await self.vector_stores.initialize_all()
            return

        missing = [key for key in store_keys if key not in self.spec.vector_stores]
        if missing:
            raise KeyError(f"Unknown vector store(s): {', '.join(missing)}")

        for store_key in store_keys:
            await self.vector_stores.initialize(store_key)

    async def initialize_graph_dependencies(self) -> None:
        store_keys = {
            node_spec.store_key
            for node_spec in self.spec.graph.nodes
            if getattr(node_spec, "kind", None) == "retriever"
        }

        if store_keys:
            await self.initialize(*store_keys)

    def build_graph(self, graph_spec: Any):
        if graph_spec.state_key not in state_registry:
            raise KeyError(f"Unknown state_key: {graph_spec.state_key}")

        state_type = state_registry[graph_spec.state_key]
        builder = StateGraph(state_type)

        for node_spec in graph_spec.nodes:
            if getattr(node_spec, "kind", None) != "conditional":
                builder.add_node(node_spec.name, self.nodes.get(node_spec.name))

        edge_sources: set[str] = set()
        edge_targets: set[str] = set()

        for edge in graph_spec.edges:
            edge_sources.add(edge.source)

            if isinstance(edge, SimpleEdgeSpec):
                builder.add_edge(edge.source, edge.target)
                edge_targets.add(edge.target)
                continue

            if isinstance(edge, RouterEdgeSpec):
                router = self.nodes.get(edge.router_key)

                path_map = dict(edge.routes)
                if edge.default_target:
                    path_map["__default__"] = edge.default_target

                edge_targets.update(edge.routes.values())
                if edge.default_target:
                    edge_targets.add(edge.default_target)

                def _route_with_default(
                    state: Any,
                    *,
                    _router=router,
                    _default=edge.default_target,
                ) -> str | None:
                    result = _router.route(state)
                    if result is None and _default:
                        return "__default__"
                    return result

                builder.add_conditional_edges(
                    edge.source,
                    _route_with_default,
                    path_map=path_map,
                )

        entry_nodes = edge_sources - edge_targets
        if not entry_nodes and graph_spec.nodes:
            entry_nodes = {graph_spec.nodes[0].name}

        for entry in entry_nodes:
            builder.add_edge(START, entry)

        leaf_nodes = edge_targets - edge_sources
        for leaf in leaf_nodes:
            builder.add_edge(leaf, END)

        compile_kwargs: dict[str, Any] = {}
        if graph_spec.compile_args.use_memory:
            compile_kwargs["checkpointer"] = MemorySaver()

        return builder.compile(**compile_kwargs)

    async def ask(self, question: str, conversation_id: str | None = None) -> str:
        if self.spec.graph.compile_args.use_memory and not conversation_id:
            raise ValueError(
                "conversation_id is required when graph memory is enabled"
            )

        input_state = {"question": question}
        config = (
            {"configurable": {"thread_id": conversation_id}}
            if conversation_id
            else None
        )

        out = await self.graph.ainvoke(input_state, config=config)
        result = out if isinstance(out, RagState) else RagState.model_validate(out)
        return result.answer