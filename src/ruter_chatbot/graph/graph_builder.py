from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ruter_chatbot.graph.node_builder import NodeBuilder
from ruter_chatbot.specs.state import state_registry
from ruter_chatbot.types.iac.edge_spec import RouterEdgeSpec, SimpleEdgeSpec
from ruter_chatbot.types.iac.graph_spec import GraphSpec


class GraphBuilder:
    def __init__(self, nodes: NodeBuilder) -> None:
        self.nodes = nodes

    def build(self, graph_spec: GraphSpec | dict[str, Any]):
        if not isinstance(graph_spec, GraphSpec):
            graph_spec = GraphSpec.model_validate(graph_spec)

        if graph_spec.state_key not in state_registry:
            raise KeyError(f"Unknown state_key: {graph_spec.state_key}")

        state_type = state_registry[graph_spec.state_key]
        builder = StateGraph(state_type)

        for node_spec in graph_spec.nodes:
            builder.add_node(node_spec.name, self.nodes.from_spec(node_spec))

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
                self._add_router_edge(builder, edge, edge_targets)
                continue

            raise TypeError(f"Unsupported edge type: {type(edge)!r}")

        self._add_entry_edges(builder, graph_spec, all_nodes, edge_targets)
        self._add_leaf_edges(builder, all_nodes, edge_sources)

        compile_kwargs: dict[str, Any] = {}
        if graph_spec.compile_args.use_memory:
            compile_kwargs["checkpointer"] = MemorySaver()

        return builder.compile(**compile_kwargs)

    def _add_router_edge(self, builder, edge: RouterEdgeSpec, edge_targets: set[str]) -> None:
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

        builder.add_conditional_edges(edge.source, _route_with_default, path_map=path_map)

    def _add_entry_edges(self, builder, graph_spec: GraphSpec, all_nodes: set[str], edge_targets: set[str]) -> None:
        entry_nodes = all_nodes - edge_targets
        if not entry_nodes and graph_spec.nodes:
            entry_nodes = {graph_spec.nodes[0].name}

        for entry in entry_nodes:
            builder.add_edge(START, entry)

    def _add_leaf_edges(self, builder, all_nodes: set[str], edge_sources: set[str]) -> None:
        leaf_nodes = all_nodes - edge_sources
        for leaf in leaf_nodes:
            builder.add_edge(leaf, END)
