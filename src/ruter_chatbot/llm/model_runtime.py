from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Type

from ruter_chatbot.types.iac.model_spec import ModelSpec
from ruter_chatbot.types.keyed import Keyed
from ruter_chatbot.types.spec_based import SpecBased


class ModelRuntime(SpecBased[ModelSpec], Keyed, ABC):
    REGISTRY: ClassVar[dict[str, Type["ModelRuntime"]]] = {}
    spec_class = ModelSpec

    def __init__(self, *, spec: ModelSpec) -> None:
        self._spec = spec

    @classmethod
    def register(cls, *model_types: str):
        def decorator(runtime_cls: Type["ModelRuntime"]) -> Type["ModelRuntime"]:
            for model_type in model_types:
                cls.REGISTRY[model_type] = runtime_cls
            return runtime_cls

        return decorator

    @classmethod
    def from_spec(cls, spec: ModelSpec) -> "ModelRuntime":
        spec_obj = ModelSpec.model_validate(spec)

        if cls is not ModelRuntime:
            return cls(spec=spec_obj)

        try:
            runtime_cls = cls.REGISTRY[spec_obj.type]
        except KeyError as exc:
            raise ValueError(f"Unsupported model type: {spec_obj.type}") from exc

        return runtime_cls(spec=spec_obj)

    def to_spec(self) -> ModelSpec:
        return self._spec.model_copy(deep=True)

    @property
    def key(self) -> str:
        return self._spec.key

    def _merged_args(self, overrides: dict[str, Any]) -> dict[str, Any]:
        return {
            **self._spec.args,
            **overrides,
        }

    @abstractmethod
    def build(self, **overrides: Any) -> Any:
        raise NotImplementedError


@ModelRuntime.register("ollama_model")
class OllamaModelRuntime(ModelRuntime):
    def build(self, **overrides: Any) -> Any:
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise RuntimeError(
                "Cannot load Ollama model: langchain-ollama is not installed.\n"
                "This is intended in production.\n"
                "Avoid using Ollama models in production."
            ) from None

        merged_args = self._merged_args(overrides)
        model_name = merged_args.get("model")

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

        return ChatOllama(**merged_args)


@ModelRuntime.register("bedrock_model")
class BedrockModelRuntime(ModelRuntime):
    def build(self, **overrides: Any) -> Any:
        import boto3

        try:
            from langchain_aws import ChatBedrockConverse
        except ImportError:
            raise RuntimeError(
                "Cannot load Bedrock model: langchain-aws is not installed."
            ) from None

        merged_args = self._merged_args(overrides)
        model_id = merged_args.get("model")
        region_name = (
            merged_args.pop("region_name", None)
            or merged_args.pop("region", None)
            or "eu-west-1"
        )

        if not model_id:
            raise ValueError("ModelSpec.args must include 'model' for bedrock_model")

        client = boto3.client("bedrock-runtime", region_name=region_name)
        return ChatBedrockConverse(client=client, **merged_args)
