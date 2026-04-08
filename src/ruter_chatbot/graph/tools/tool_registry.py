from __future__ import annotations

from typing import Any
from typing import Iterable

from ruter_chatbot.graph.tools.tool_runtime import ToolRuntime
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.iac.tool_spec import ToolSpec
from ruter_chatbot.types.spec_based_registry import SpecBasedRegistry


class ToolRegistry(
    SpecBasedRegistry[
        ToolRuntime, ToolSpec
    ]
):
    runtime_class = ToolRuntime

    def __init__(
        self,
        vector_stores: VectorStoreRegistry,
        items: Iterable[ToolRuntime | ToolSpec] | None = None,
    ) -> None:
        self.vector_stores = vector_stores
        super().__init__(items)

    @classmethod
    def from_spec(
        cls,
        specs: dict[str, ToolSpec] | None,
        vector_stores: VectorStoreRegistry,
    ) -> "ToolRegistry":
        return super().from_spec(specs, vector_stores=vector_stores)

    def add(self, obj: ToolRuntime | ToolSpec) -> ToolRuntime:
        if isinstance(obj, ToolRuntime):
            runtime = obj
        else:
            runtime = ToolRuntime.from_spec_with_dependencies(
                obj,
                vector_stores=self.vector_stores,
            )
        self._items[runtime.key] = runtime
        return runtime

    def get_many(self, keys: list[str]) -> list[Any]:
        return [self.build(key) for key in keys]

    def build(self, key: str) -> Any:
        return self.get(key).build()
