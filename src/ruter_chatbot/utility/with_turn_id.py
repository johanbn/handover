'''
Provides function:
    with_turn_id: Attach turn_id safely to any message using model_copy.
'''
from uuid import UUID
from langchain_core.messages import BaseMessage

def with_turn_id(message: BaseMessage, turn_id: UUID) -> BaseMessage:
    """Attach turn_id to any message's additional_kwargs"""
    if not hasattr(message, "additional_kwargs"):
        message.additional_kwargs = {}
    
    message.additional_kwargs["turn_id"] = turn_id
    
    return message
