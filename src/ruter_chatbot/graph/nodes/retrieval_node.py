from __future__ import annotations

from typing import Literal
from langchain_core.documents import Document

from ruter_chatbot.graph.nodes.base import BaseNode
from ruter_chatbot.graph.policies.input import apply_history_window_to_docs
from ruter_chatbot.graph.policy import GraphPolicy
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.iac.node_spec import RetrieverNodeSpec
from ruter_chatbot.types.iac.state_spec import RagState


class RetrievalNode(BaseNode):
    def __init__(
        self,
        *,
        vector_stores: VectorStoreRegistry,
        name: str,
        store_key: str,
        top_k: int = 5,
        search_type: Literal["similarity", "scored_similarity", "mmr"] = "similarity",
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        output_key: str = "docs",
        policy: GraphPolicy
    ) -> None:
        self.vector_stores = vector_stores
        self.name = name
        self.store_key = store_key
        self.top_k = top_k
        self.search_type = search_type
        self.fetch_k = fetch_k
        self.lambda_mult = lambda_mult
        self.output_key = output_key
        self.policy = policy

    @classmethod
    def from_spec(
        cls,
        spec: RetrieverNodeSpec,
        vector_stores: VectorStoreRegistry,
        policy: GraphPolicy
    ) -> "RetrievalNode":
        vector_stores.get(spec.store_key)

        return cls(
            vector_stores=vector_stores,
            name=spec.name,
            store_key=spec.store_key,
            top_k=spec.top_k,
            search_type=spec.search_type,
            fetch_k=spec.fetch_k,
            lambda_mult=spec.lambda_mult,
            output_key=spec.output_key,
            policy=policy,
        )

    def to_spec(self) -> RetrieverNodeSpec:
        return RetrieverNodeSpec(
            kind="retriever",
            name=self.name,
            store_key=self.store_key,
            search_type=self.search_type,
            top_k=self.top_k,
            fetch_k=self.fetch_k,
            lambda_mult=self.lambda_mult,
            output_key=self.output_key,
        )

    def __call__(
        self,
        state: RagState,
    ) -> dict[str, list[Document]]:
        search_query = state.query or state.question
        turn_id = state.turn_id
        old_docs = state.docs or []
        new_docs = []

        store = self.vector_stores.get(self.store_key)

        if "similarity" in self.search_type:
            results = store.similarity_search(
                search_query,
                k=self.top_k,
                with_score=self.search_type == "scored_similarity",
            )

        elif self.search_type == "mmr":
            results = store.max_marginal_relevance_search(
                search_query,
                k=self.top_k,
                fetch_k=self.fetch_k,
                lambda_mult=self.lambda_mult,
            )
        else:
            raise ValueError(f"Unsupported search_type: {self.search_type}")
        
        
        for doc in results:
            score = None
            if isinstance(doc, tuple):
                doc, score = doc
            doc.metadata = doc.metadata or {}
            doc.metadata["turn_id"] = turn_id
            if score:
                doc.metadata["score"] = float(score)
            new_docs.append(doc)

        docs: dict[str, Document] = {}
        for doc in old_docs:
            doc_id = doc.metadata.get("doc_id")
            if doc_id is not None:
                docs[doc_id] = doc
        
        for doc in new_docs:
            doc_id = doc.metadata.get("doc_id")
            if doc_id is not None:
                docs[doc_id] = doc # overwrite is fine since its the same source.

        return {
            self.output_key: apply_history_window_to_docs(
                list(docs.values()),
                policy=self.policy
            ),
            "query": None # reset to favor user questions.
        }
