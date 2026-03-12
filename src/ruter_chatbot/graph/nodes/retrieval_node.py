from __future__ import annotations

from typing import Any

from ruter_chatbot.graph.nodes.base import BaseNode
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.iac.node_spec import RetrieverNodeSpec
from ruter_chatbot.types.iac.state_spec import RagState


class RetrievalNode(BaseNode):
    def __init__(
        self,
        *,
        store: Any,
        top_k: int = 5,
        with_score: bool = False,
        output_key: str = "docs",
    ) -> None:
        self.store = store
        self.top_k = top_k
        self.with_score = with_score
        self.output_key = output_key

    @classmethod
    def from_spec(
        cls,
        spec: RetrieverNodeSpec,
        **deps: Any,
    ) -> "RetrievalNode":
        vector_stores: VectorStoreRegistry = deps["vector_stores"]

        return cls(
            store=vector_stores.get(spec.store_key),
            top_k=spec.top_k,
            with_score=spec.with_score,
            output_key=spec.output_key,
        )

    def __call__(self, state: RagState) -> dict[str, Any]:
        docs = self.store.similarity_search(
            state.question,
            k=self.top_k,
            with_score=self.with_score,
        )
        return {self.output_key: docs}