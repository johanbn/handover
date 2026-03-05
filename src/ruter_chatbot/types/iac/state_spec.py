'''
Defines custom states for Langgraph StateGraphs - not StateSpec.
Use:

from ruter_chatbot.types.iac.state_spec import *
'''
from typing import Annotated
from pydantic import BaseModel
from langchain_core.documents import Document
from langgraph.graph.message import add_messages, AnyMessage

class RagState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    question: str
    docs: list[Document]
    context: str
    answer: str
