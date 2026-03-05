from typing import Any, Dict

from pydantic import BaseModel, Field


class ProviderSpec(BaseModel):
    type: str
    args: Dict[str, Any] = Field(default_factory=dict)
