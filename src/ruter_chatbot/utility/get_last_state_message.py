'''
Provides function:
    get_last_state_message:
        Returns the last message of from `messages`
        Can target specific types and return last of that kind.
        Returns None if none qualified.
'''
from typing import Any, Optional

from langchain_core.messages import (
    BaseMessage,
)

from ruter_chatbot.types.app.ask import AskState

def get_last_state_message(
    state: AskState | dict[str, Any],
    target_type: Optional[BaseMessage]
) -> str:
    '''
    Returns the last LangChain message from `messages` on state.
    Supports pydantic models and dictionaries.
    Can target specific types and return last of that kind.
    Returns None if none qualified.
    '''
    messages = (
        state.get("messages")
        if isinstance(state, dict)
        else getattr(state, "messages", None)
    )

    if not messages:
        return None
    
    if not target_type:
        return messages[-1]
    
    for msg in reversed(messages):
        if isinstance(msg, target_type):
            return msg
    
    return None