from pydantic import BaseModel

from ruter_chatbot.specs.state import AskState


class AskResponse(BaseModel):
    answer: str
    conversation_id: str | None = None
    state: AskState | None = None


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    debug: bool = False