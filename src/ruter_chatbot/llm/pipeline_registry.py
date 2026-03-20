from __future__ import annotations

from typing import Any

from ruter_chatbot.llm.model_registry import ModelRegistry
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec


class PipelineRegistry:
    def __init__(self, models: ModelRegistry) -> None:
        self.models = models
        self.pipelines: dict[str, dict[str, Any]] = {}

    def from_spec(self, spec: PipelineSpec) -> None:
        if spec.type not in {"ollama_pipeline", "bedrock_pipeline", "chat"}:
            raise ValueError(f"Unsupported pipeline type: {spec.type}")

        self.pipelines[spec.key] = {
            "type": spec.type,
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

    def build(self, key: str) -> Any:
        if key not in self.pipelines:
            raise KeyError(f"Unknown pipeline key: {key}")

        pipeline = self.pipelines[key]
        model_entry = self.models.get(pipeline["model_key"])

        model_args = dict(model_entry["args"])
        pipeline_args = dict(pipeline["args"])

        merged_args = {
            **model_args,
            **pipeline_args,
        }

        provider = model_entry.get("provider")

        if provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
            except ImportError:
                raise RuntimeError(
                    "Cannot load Ollama model: langchain-ollama is not installed.\n"
                    "This is intended in production.\n"
                    "Avoid using Ollama models in production."
                ) from None

            return ChatOllama(**merged_args)

        if provider == "bedrock":
            import boto3
            try:
                from langchain_aws import ChatBedrockConverse
            except ImportError:
                raise RuntimeError(
                    "Cannot load Bedrock model: langchain-aws is not installed."
                ) from None

            region_name = (
                merged_args.pop("region_name", None)
                or merged_args.pop("region", None)
                or "eu-west-1"
            )

            client = boto3.client("bedrock-runtime", region_name=region_name)

            return ChatBedrockConverse(
                client=client,
                **merged_args,
            )

        raise ValueError(f"Unsupported model provider: {provider}")
