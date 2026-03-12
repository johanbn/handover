from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ruter_chatbot.graph.node_registry import NodeRegistry
from ruter_chatbot.llm.model_registry import ModelRegistry
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.iac.edge_spec import RouterEdgeSpec, SimpleEdgeSpec
from ruter_chatbot.types.iac.graph_spec import GraphSpec
from ruter_chatbot.types.iac.model_spec import ModelSpec
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.state_spec import RagState
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec

# why this?
STATE_TYPES = {
    "rag_state": RagState,
}


class Orchestrator:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg

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

        self.graph = None
        if "graph" in self.cfg:
            self.graph = self.build_graph(GraphSpec.model_validate(self.cfg["graph"]))

        self.state = RagState()

    def _load_specs(self) -> None:
        for item in self.cfg.get("models", []):
            self.models.from_spec(ModelSpec.model_validate(item))

        for item in self.cfg.get("pipelines", []):
            self.pipelines.from_spec(PipelineSpec.model_validate(item))

        for item in self.cfg.get("prompts", []):
            spec = PromptSpec.model_validate(item)
            self.prompts[spec.key] = spec

        for item in self.cfg.get("vector_stores", []):
            if isinstance(item, VectorStoreSpec):
                self.vector_stores.from_spec(item)
            else:
                self.vector_stores.from_spec(VectorStoreSpec.model_validate(item))

        graph_spec = GraphSpec.model_validate(self.cfg["graph"])
        for node_spec in graph_spec.nodes:
            self.nodes.from_spec(node_spec)

    async def initialize(self) -> None:
        await self.vector_stores.initialize_all()

    def build_graph(self, graph_spec: GraphSpec):
        if graph_spec.state_key not in STATE_TYPES:
            raise KeyError(f"Unknown state_key: {graph_spec.state_key}")

        state_type = STATE_TYPES[graph_spec.state_key]
        builder = StateGraph(state_type)

        for node_spec in graph_spec.nodes:
            if getattr(node_spec, "kind", None) != "conditional":
                builder.add_node(node_spec.name, self.nodes.get(node_spec.name))

        for edge in graph_spec.edges:
            if isinstance(edge, SimpleEdgeSpec):
                builder.add_edge(edge.source, edge.target)

            elif isinstance(edge, RouterEdgeSpec):
                router = self.nodes.get(edge.router_key)

                path_map = dict(edge.routes)
                if edge.default_target:
                    path_map["__default__"] = edge.default_target

                def _route_with_default(state, _router=router, _default=edge.default_target):
                    result = _router.route(state)
                    if result is None and _default:
                        return "__default__"
                    return result

                builder.add_conditional_edges(
                    edge.source,
                    _route_with_default,
                    path_map=path_map,
                )

        start_targets = {e.source for e in graph_spec.edges}
        edge_targets = set()

        for edge in graph_spec.edges:
            if isinstance(edge, SimpleEdgeSpec):
                edge_targets.add(edge.target)
            elif isinstance(edge, RouterEdgeSpec):
                edge_targets.update(edge.routes.values())
                if edge.default_target:
                    edge_targets.add(edge.default_target)

        entry_nodes = start_targets - edge_targets
        if not entry_nodes and graph_spec.nodes:
            entry_nodes = {graph_spec.nodes[0].name}

        for entry in entry_nodes:
            builder.add_edge(START, entry)

        all_sources = {e.source for e in graph_spec.edges}
        leaf_nodes = edge_targets - all_sources
        for leaf in leaf_nodes:
            builder.add_edge(leaf, END)

        return builder.compile()

    def set_temperature(self, pipeline_key: str, value: float) -> None:
        self.pipelines.update(pipeline_key, temperature=value)

    async def ask(self, question: str) -> str:
        if self.graph is None:
            raise RuntimeError("Graph has not been built")

        self.state.question = question
        self.state.messages = self.state.messages + []

        out = self.graph.invoke(self.state)
        self.state = out if isinstance(out, RagState) else RagState.model_validate(out)

        return self.state.answer