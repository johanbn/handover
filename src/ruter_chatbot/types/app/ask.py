from typing import Any
from pydantic import BaseModel, Field


class AskResponse(BaseModel):
    answer: str
    conversation_id: str | None = None
    state: dict[str, Any] | None = None


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    debug: bool = False