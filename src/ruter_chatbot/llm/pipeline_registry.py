from __future__ import annotations

from typing import Any

from langchain_ollama import ChatOllama

from ruter_chatbot.llm.model_registry import ModelRegistry
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec


class PipelineRegistry:
    def __init__(self, models: ModelRegistry) -> None:
        self.models = models
        self.pipelines: dict[str, dict[str, Any]] = {}

    def from_spec(self, spec: PipelineSpec) -> None:
        if spec.type != "ollama_pipeline":
            raise ValueError(f"Unsupported pipeline type: {spec.type}")

        self.pipelines[spec.key] = {
            "model_key": spec.model_key,
            "args": dict(spec.args),
        }

    def update(self, key: str, **new_args: Any) -> None:
        if key not in self.pipelines:
            raise KeyError(f"Unknown pipeline key: {key}")

        self.pipelines[key]["args"] = {
            **self.pipelines[key]["args"],
            **new_args,
        }

    def build(self, key: str) -> ChatOllama:
        if key not in self.pipelines:
            raise KeyError(f"Unknown pipeline key: {key}")

        pipeline = self.pipelines[key]
        model_entry = self.models.get(pipeline["model_key"])

        merged_args = {
            **model_entry["args"],
            **pipeline["args"],
        }

        return ChatOllama(**merged_args)