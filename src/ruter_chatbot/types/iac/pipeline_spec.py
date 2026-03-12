from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel, Field


class PipelineSpec(BaseModel):
    key: str
    type: str
    model_key: str
    args: Dict[str, Any] = Field(default_factory=dict)
