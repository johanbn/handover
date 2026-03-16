from __future__ import annotations

from typing import Any, Literal

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
        search_type: Literal["similarity", "mmr"] = "similarity",
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        output_key: str = "docs",
    ) -> None:
        self.store = store
        self.top_k = top_k
        self.with_score = with_score
        self.search_type = search_type
        self.fetch_k = fetch_k
        self.lambda_mult = lambda_mult
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
            search_type=spec.search_type,
            fetch_k=spec.fetch_k,
            lambda_mult=spec.lambda_mult,
            output_key=spec.output_key,
        )

    def __call__(self, state: RagState) -> dict[str, Any]:
        if self.search_type == "similarity":
            results = self.store.similarity_search(
                state.question,
                k=self.top_k,
                with_score=self.with_score,
            )

            if self.with_score:
                docs = []
                for doc, score in results:
                    doc.metadata = doc.metadata or {}
                    doc.metadata["score"] = float(score)
                    docs.append(doc)
                return {self.output_key: docs}

            return {self.output_key: results}

        if self.search_type == "mmr":
            if self.with_score:
                raise ValueError("with_score=True is not supported together with search_type='mmr'")

            results = self.store.max_marginal_relevance_search(
                state.question,
                k=self.top_k,
                fetch_k=self.fetch_k,
                lambda_mult=self.lambda_mult,
            )
            return {self.output_key: results}

        raise ValueError(f"Unsupported search_type: {self.search_type}")