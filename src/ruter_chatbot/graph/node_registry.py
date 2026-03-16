from __future__ import annotations

from typing import Any

from ruter_chatbot.graph.nodes.llm_node import LLMNode
from ruter_chatbot.graph.nodes.retrieval_node import RetrievalNode
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec, RetrieverNodeSpec


class NodeRegistry:
    def __init__(self, **deps: Any) -> None:
        self._deps = deps
        self._nodes: dict[str, Any] = {}

    def from_spec(self, spec: Any) -> None:
        if isinstance(spec, LLMNodeSpec):
            node = LLMNode.from_spec(spec, **self._deps)
        elif isinstance(spec, RetrieverNodeSpec):
            node = RetrievalNode.from_spec(spec, **self._deps)
        else:
            raise TypeError(f"Unsupported node spec type: {type(spec).__name__}")

        self._nodes[spec.name] = node

    def get(self, key: str) -> Any:
        if key not in self._nodes:
            raise KeyError(f"Unknown node key: {key}")
        return self._nodes[key]