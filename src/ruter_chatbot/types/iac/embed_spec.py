
from typing import Any, Dict

from pydantic import BaseModel, Field


class EmbedSpec(BaseModel):
    type: str
    args: Dict[str, Any] = Field(default_factory=dict)
