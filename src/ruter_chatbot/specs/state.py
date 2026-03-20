from typing import TypeAlias
from langgraph.graph.state import StateT
from langgraph.graph.message import MessagesState
from ruter_chatbot.types.iac.state_spec import RagState

"""
If you add something to state_registry you need to add states
"""

AskState: TypeAlias = MessagesState | RagState

state_registry: dict[str, StateT] = {
    "messages": MessagesState,
    "structured_rag": RagState,
}
'''
Registry of supported state formats and how to refer to them.
'''
