'''
Provides functions that apply output-oriented policies.
'''
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage
)

from ruter_chatbot.graph.policy import GraphPolicy
from ruter_chatbot.graph.policies.utils import is_context_message

def  sanitize_messages_for_output(
    messages: list[BaseMessage],
    policy: GraphPolicy
) -> list[BaseMessage]:
    '''Applies the output-related policies in order of priority.'''
    if not messages:
        return []
    
    def should_persist(msg: BaseMessage) -> bool:
        if not isinstance(msg, (SystemMessage, HumanMessage)):
            # policies do not apply to other types
            return True
        if not policy.persist_prompt_scaffolding:
            return False
        if is_context_message(msg):
            return policy.persist_context_messages
        if isinstance(msg, SystemMessage):
            return policy.persist_system_messages
        
        # we shouldn't ever reach this but for the sake of completeness
        return True
    
    return [msg for msg in messages if should_persist(msg)]
