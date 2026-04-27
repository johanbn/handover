from __future__ import annotations

from typing import Any

from ruter_chatbot.llm.model_runtime import ModelRuntime
from ruter_chatbot.types.iac.model_spec import ModelSpec
from ruter_chatbot.types.spec_based_registry import SpecBasedRegistry

class ModelRegistry(
    SpecBasedRegistry[
        ModelRuntime, ModelSpec
    ]
):
    runtime_class = ModelRuntime

    def build(self, key: str, **overrides: Any) -> Any:
        return self.get(key).build(**overrides)
