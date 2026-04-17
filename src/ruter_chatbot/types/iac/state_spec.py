'''
Defines custom states for Langgraph StateGraphs - not StateSpec.
Use:

from ruter_chatbot.types.iac.state_spec import *
'''
from typing import Annotated
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class RagState(BaseModel):
    turn_id: UUID
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    question: str = ""
    docs: list[Document] = Field(default_factory=list)
    context: str = ""
    answer: str = ""
    route: str = ""