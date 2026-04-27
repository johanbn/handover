from typing import Any

from pydantic import BaseModel, Field


class GenericSpec(BaseModel):
    type: str
    args: dict[str, Any] = Field(default_factory=dict)