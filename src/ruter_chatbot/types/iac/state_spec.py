'''
Defines custom states for Langgraph StateGraphs - not StateSpec.
Use:

from ruter_chatbot.types.iac.state_spec import *
'''
from typing import Annotated

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field


class RagState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    question: str = ""
    docs: list[Document] = Field(default_factory=list)
    context: str = ""
    answer: str = ""
    route: str = ""