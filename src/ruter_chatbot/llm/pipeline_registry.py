from __future__ import annotations

from typing import Any, Iterable

from ruter_chatbot.llm.model_registry import ModelRegistry
from ruter_chatbot.llm.pipeline_runtime import PipelineRuntime
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec
from ruter_chatbot.types.spec_based_registry import SpecBasedRegistry

class PipelineRegistry(
    SpecBasedRegistry[
        PipelineRuntime, PipelineSpec
    ]
):
    runtime_class = PipelineRuntime

    def __init__(
        self,
        models: ModelRegistry,
        items: Iterable[PipelineRuntime | PipelineSpec] | None = None,
    ) -> None:
        super().__init__(items)
        self.models = models

    @classmethod
    def from_spec(
        cls,
        specs: dict[str, PipelineSpec] | None,
        models: ModelRegistry,
    ) -> "PipelineRegistry":
        return super().from_spec(specs, models=models)


    def update(self, key: str, **new_args: Any) -> None:
        if key not in self:
            raise KeyError(f"Unknown pipeline key: {key}")

        self._items[key] = self._items[key].updated(**new_args)

    def build(self, key: str) -> Any:
        return self.get(key).build(self.models)
