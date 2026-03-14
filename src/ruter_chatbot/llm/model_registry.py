from __future__ import annotations

import subprocess
from typing import Any

import boto3
from langchain_aws import ChatBedrockConverse
from langchain_ollama import ChatOllama

from ruter_chatbot.types.iac.model_spec import ModelSpec


class ModelRegistry:
    def __init__(self) -> None:
        self.models: dict[str, dict[str, Any]] = {}

    def from_spec(self, spec: ModelSpec) -> None:
        if spec.type == "ollama_model":
            self._load_ollama_model(spec)
        elif spec.type == "bedrock_model":
            self._load_bedrock_model(spec)
        else:
            raise ValueError(f"Unsupported model type: {spec.type}")

    def _load_ollama_model(self, spec: ModelSpec) -> None:
        model_name = spec.args.get("model")
        if not model_name:
            raise ValueError("ModelSpec.args must include 'model' for ollama_model")

        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=False,
        )

        if model_name not in result.stdout:
            subprocess.run(["ollama", "pull", model_name], check=True)

        self.models[spec.key] = {
            "model": ChatOllama(**spec.args),
            "args": dict(spec.args),
            "provider": "ollama",
        }

    def _load_bedrock_model(self, spec: ModelSpec) -> None:
        model_id = spec.args.get("model")
        region_name = spec.args.get("region_name") or spec.args.get("region") or "eu-west-1"

        if not model_id:
            raise ValueError("ModelSpec.args must include 'model' for bedrock_model")

        client = boto3.client("bedrock-runtime", region_name=region_name)

        model_kwargs = {
            k: v
            for k, v in spec.args.items()
            if k not in {"region_name", "region"}
        }

        self.models[spec.key] = {
            "model": ChatBedrockConverse(
                client=client,
                **model_kwargs,
            ),
            "args": dict(spec.args),
            "provider": "bedrock",
        }

    def get(self, key: str) -> dict[str, Any]:
        if key not in self.models:
            raise KeyError(f"Unknown model key: {key}")
        return self.models[key]