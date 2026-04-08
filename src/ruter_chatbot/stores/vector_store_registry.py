from __future__ import annotations

from ruter_chatbot.stores.vector_store_runtime import VectorStoreRuntime
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.types.spec_based_registry import SpecBasedRegistry
from ruter_chatbot.types.app.vector_store import (
    VectorStoreInfo,
    VectorStoreListResponse,
)

class VectorStoreRegistry(
    SpecBasedRegistry[
        VectorStoreRuntime, VectorStoreSpec
    ]
):
    runtime_class = VectorStoreRuntime

    def initialize(self, key: str) -> None:
        self.get(key).initialize()

    def initialize_all(self) -> None:
        for store in self._items.values():
            store.initialize()

    def refresh(self, key: str) -> None:
        self.get(key).refresh()

    def start_refresh(self, key: str):
        return self.get(key).start_refresh()

    def list_stores(self) -> VectorStoreListResponse:
        stores: list[VectorStoreRuntime] = list(self._items.values())
        return VectorStoreListResponse(
            stores=[
                VectorStoreInfo(
                    name=store.key,
                    state=store.state.value,
                )
                for store in stores
            ]
        )
