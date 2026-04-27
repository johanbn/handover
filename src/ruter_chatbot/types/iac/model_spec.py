from typing import Any

from pydantic import BaseModel, Field


class ModelSpec(BaseModel):
    key: str
    type: str
    args: dict[str, Any] = Field(default_factory=dict)