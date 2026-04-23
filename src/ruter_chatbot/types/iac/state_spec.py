'''
Defines custom states for Langgraph StateGraphs - not StateSpec.
Use:

from ruter_chatbot.types.iac.state_spec import *
'''
from typing import Annotated, Any
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

def last_value(_old: Any, new: Any) -> Any:
    """Last write wins."""
    return new

class RagState(BaseModel):
    turn_id: UUID
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    question: str = ""
    '''question always comes from a user.'''
    query: Annotated[str | None, last_value] = None
    '''query comes from tools and takes priority when it exists -> should be reset after use.'''
    docs: list[Document] = Field(default_factory=list)
    answer: str = ""
    route: Annotated[str | None, last_value] = None