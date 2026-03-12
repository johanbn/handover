from __future__ import annotations

from typing import Any, Dict

from langchain_ollama import ChatOllama

from ruter_chatbot.types.iac.model_spec import ModelSpec


class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, Dict[str, Any]] = {}

    def from_spec(self, spec: ModelSpec) -> None:
        if spec.type != "ollama_model":
            raise KeyError(f"Unsupported model type: {spec.type}")

        self.models[spec.key] = {
            "model": ChatOllama(**spec.args),
            "args": dict(spec.args),
        }

    def get(self, key: str) -> Dict[str, Any]:
        if key not in self.models:
            raise KeyError(f"Unknown model_key: {key}")
        return self.models[key]