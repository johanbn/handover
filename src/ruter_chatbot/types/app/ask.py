from pydantic import BaseModel, Field

from langchain_core.documents import Document

from ruter_chatbot.specs.state import AskState


class AskResponse(BaseModel):
    answer: str
    conversation_id: str | None = None
    docs: list[Document] = []
    state: AskState | None = None


class AskRequest(BaseModel):
    question: str = Field(
        description="A question for the RAG-LLM chatbot.",
        examples=["What is love?"]
    )
    conversation_id: str | None = Field(
        default=None,
        description=(
            "Optional ID of an existing conversation to continue with memory. "
            "Omit the field entirely or send null to start a new conversation."
        ),
        examples=[None, "conv-abc123-uuid-here"],
    )
    debug: bool = Field(
        default=False,
        description="If true, include the full internal graph state in the response (for debugging only).",
        examples=[False, True],
    )