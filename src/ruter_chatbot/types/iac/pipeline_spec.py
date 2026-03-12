from typing import Any

from pydantic import BaseModel, Field


class PipelineSpec(BaseModel):
    key: str
    type: str
    model_key: str
    args: dict[str, Any] = Field(default_factory=dict)