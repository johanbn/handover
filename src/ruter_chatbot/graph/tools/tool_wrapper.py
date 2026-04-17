from typing import Callable
from uuid import UUID

from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest, ToolCallWrapper
from langgraph.types import Command

from ruter_chatbot.utility.with_turn_id import with_turn_id

def tool_wrapper(
    request: ToolCallRequest,
    execute: Callable[[ToolCallRequest], ToolMessage | Command]
) -> ToolMessage | Command:
    """
    Wrapper that does generically necessary operations on Tool calls.
    """
    # add pre-tool ops here if needed

    result = execute(request)

    # Ensure turn_ids exist on outgoing messages.
    turn_id: UUID | None = None
    if hasattr(request, "state") and request.state is not None:
        state = request.state

        if isinstance(state, dict):
            turn_id = state.get("turn_id")
        else:
            turn_id = getattr(state, "turn_id", None)
    
    if turn_id is None:
        return result
    
    if isinstance(result, ToolMessage):
        result = with_turn_id(message=result, turn_id=turn_id)

    elif isinstance(result, Command) and isinstance(result.update, dict):
        messages = result.update.get("messages")
        if messages is not None:
            if not isinstance(messages, list):
                messages = [messages]
            for msg in messages:
                if isinstance(msg, ToolMessage):
                    with_turn_id(message=msg, turn_id=turn_id)
    
    return result
