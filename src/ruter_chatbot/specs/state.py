from langgraph.graph.state import StateT
from langgraph.graph.message import MessagesState
from types.iac.state_spec import *

state_registry: dict[str, StateT] = {
    "messages": MessagesState,
    "structured_rag": RagState,
}
