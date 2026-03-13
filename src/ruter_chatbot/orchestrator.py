from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from ruter_chatbot.graph.node_registry import NodeRegistry
from ruter_chatbot.llm.model_registry import ModelRegistry
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.iac.app_spec import AppSpec
from ruter_chatbot.types.iac.edge_spec import RouterEdgeSpec, SimpleEdgeSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.state_spec import RagState
from ruter_chatbot.specs.state import state_registry


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
        self.state = RagState()

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

    async def initialize(self) -> None:
        await self.vector_stores.initialize_all()

    def build_graph(self, graph_spec):
        if graph_spec.state_key not in state_registry:
            raise KeyError(f"Unknown state_key: {graph_spec.state_key}")

        state_type = state_registry[graph_spec.state_key]
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

                def _route_with_default(
                    state,
                    _router=router,
                    _default=edge.default_target,
                ):
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
        if pipeline_key not in self.spec.pipelines:
            raise KeyError(f"Unknown pipeline: {pipeline_key}")

        self.spec.pipelines[pipeline_key].args["temperature"] = value
        self.pipelines.update(pipeline_key, temperature=value)

    async def ask(self, question: str) -> str:
        self.state.question = question
        out = self.graph.invoke(self.state)
        self.state = out if isinstance(out, RagState) else RagState.model_validate(out)
        return self.state.answer