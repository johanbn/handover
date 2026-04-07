from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec
from ruter_chatbot.types.keyed import Keyed
from ruter_chatbot.types.spec_based import SpecBased

if TYPE_CHECKING:
    from ruter_chatbot.llm.model_registry import ModelRegistry


class PipelineRuntime(SpecBased[PipelineSpec], Keyed):
    SUPPORTED_TYPES = {"ollama_pipeline", "bedrock_pipeline", "chat"}
    spec_class = PipelineSpec

    def __init__(self, *, spec: PipelineSpec) -> None:
        self._spec = spec

    @classmethod
    def from_spec(cls, spec: PipelineSpec) -> "PipelineRuntime":
        spec_obj = PipelineSpec.model_validate(spec)

        if spec_obj.type not in cls.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported pipeline type: {spec_obj.type}")

        return cls(spec=spec_obj)

    def to_spec(self) -> PipelineSpec:
        return self._spec.model_copy(deep=True)

    @property
    def key(self) -> str:
        return self._spec.key

    def updated(self, **new_args: Any) -> "PipelineRuntime":
        updated_spec = self._spec.model_copy(
            update={
                "args": {
                    **self._spec.args,
                    **new_args,
                }
            },
            deep=True,
        )
        return self.from_spec(updated_spec)

    def build(self, models: "ModelRegistry") -> Any:
        return models.build(self._spec.model_key, **self._spec.args)
