from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel, Field


class ModelSpec(BaseModel):
    key: str
    type: str
    args: Dict[str, Any] = Field(default_factory=dict)
