'''
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
