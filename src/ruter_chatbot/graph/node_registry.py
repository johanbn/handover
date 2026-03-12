from __future__ import annotations

from typing import Any, cast

from pydantic import TypeAdapter

from ruter_chatbot.graph.nodes.conditional_node import ConditionalNode
from ruter_chatbot.graph.nodes.llm_node import LLMNode
from ruter_chatbot.graph.nodes.retrieval_node import RetrievalNode
from ruter_chatbot.types.iac.node_spec import (
    ConditionalNodeSpec,
    LLMNodeSpec,
    NodeSpec,
    RetrieverNodeSpec,
)


class NodeRegistry:
    def __init__(self, **deps: Any) -> None:
        self.deps = deps
        self.nodes: dict[str, Any] = {}

    def from_spec(self, spec: NodeSpec | dict[str, Any]) -> None:
        if isinstance(spec, dict):
            spec = TypeAdapter(NodeSpec).validate_python(spec)

        if isinstance(spec, LLMNodeSpec):
            node = LLMNode.from_spec(spec, **self.deps)

        elif isinstance(spec, RetrieverNodeSpec):
            node = RetrievalNode.from_spec(spec, **self.deps)

        elif isinstance(spec, ConditionalNodeSpec):
            node = ConditionalNode.from_spec(spec, **self.deps)

        else:
            raise ValueError(f"Unsupported node spec type: {type(spec)}")

        self.nodes[spec.name] = node

    def get(self, name: str) -> Any:
        if name not in self.nodes:
            raise KeyError(f"Unknown node: {name}")
        return self.nodes[name]