from __future__ import annotations

from ruter_chatbot.stores.vector_store import VectorStore
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec


class VectorStoreRegistry:
    def __init__(self) -> None:
        self.vector_stores: dict[str, VectorStore] = {}

    def from_spec(self, spec: VectorStoreSpec) -> None:
        self.vector_stores[spec.name] = VectorStore.from_spec(spec)

    def get(self, name: str) -> VectorStore:
        if name not in self.vector_stores:
            raise KeyError(f"Unknown vector store: {name}")
        return self.vector_stores[name]

    async def initialize(self, name: str) -> None:
        store = self.get(name)
        await store.initialize()

    async def initialize_all(self) -> None:
        for store in self.vector_stores.values():
            await store.initialize()