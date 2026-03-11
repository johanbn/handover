from typing import Any, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field


class Source(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")
    type: Literal["filesystem", "confluence"]
    location: str 
    meta: Dict[str, Any] = Field(default_factory=dict)
