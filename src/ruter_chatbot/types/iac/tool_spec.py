from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    key: str
    type: Literal["builtin"]
    args: dict[str, Any] = Field(default_factory=dict)
