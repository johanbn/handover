from __future__ import annotations

import subprocess
from typing import Any

from langchain_ollama import ChatOllama

from ruter_chatbot.types.iac.model_spec import ModelSpec


class ModelRegistry:
    def __init__(self) -> None:
        self.models: dict[str, dict[str, Any]] = {}

    def from_spec(self, spec: ModelSpec) -> None:
        if spec.type != "ollama_model":
            raise ValueError(f"Unsupported model type: {spec.type}")

        model_name = spec.args.get("model")
        if not model_name:
            raise ValueError("ModelSpec.args must include 'model'")

        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
        )

        if model_name not in result.stdout:
            subprocess.run(["ollama", "pull", model_name], check=True)

        self.models[spec.key] = {
            "model": ChatOllama(**spec.args),
            "args": dict(spec.args),
        }

    def get(self, key: str) -> dict[str, Any]:
        if key not in self.models:
            raise KeyError(f"Unknown model key: {key}")
        return self.models[key]