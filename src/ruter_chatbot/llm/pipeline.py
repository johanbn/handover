from __future__ import annotations

from typing import Any, Dict

from langchain_ollama import ChatOllama

from ruter_chatbot.llm.model import ModelRegistry
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec


class PipelineRegistry:
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry
        self.pipelines: Dict[str, Dict[str, Any]] = {}

    def from_spec(self, spec: PipelineSpec) -> None:
        if spec.type != "ollama_pipeline":
            raise KeyError(f"Unsupported pipeline type: {spec.type}")

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
        model_entry = self.model_registry.get(pipeline["model_key"])

        merged_args = {
            **model_entry["args"],
            **pipeline["args"],
        }

        return ChatOllama(**merged_args)