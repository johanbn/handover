from langgraph.graph.state import StateT
from langgraph.graph.message import MessagesState
from ruter_chatbot.types.iac.state_spec import RagState

state_registry: dict[str, StateT] = {
    "messages": MessagesState,
    "structured_rag": RagState,
}
'''
Registry of supported state formats and how to refer to them.
'''
