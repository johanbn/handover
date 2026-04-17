'''
Provides functions that apply input-oriented policies.
These 
'''
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage

from ruter_chatbot.graph.policy import GraphPolicy

def apply_history_window_to_messages(
    messages: list[BaseMessage],
    policy: GraphPolicy,
) -> list[BaseMessage]:
    """
    Apply history_window.
    The window counts turns by the number of discrete turn_ids.
    It returns all messages after the turn_id `policy.history_window` turns ago.
    NOTE: Assumes the messages are provided in chronological order!
    """
    window = policy.history_window
    if window <= 0:
        # for the 0 case all messages are from the current turn
        return messages

    # collect turn ids in reverse
    seen: set[UUID] = set()
    keep_turns: list[UUID] = []
    for msg in reversed(messages):
        turn_id: UUID = msg.additional_kwargs["turn_id"]
        if turn_id not in seen:
            seen.add(turn_id)
            keep_turns.append(turn_id)
            if len(keep_turns) == window:
                break
    
    keep_set = set(keep_turns)

    return [
        msg
        for msg in messages
        if msg.additional_kwargs["turn_id"] in keep_set
    ]

def apply_history_window_to_docs(
    docs: list[Document],
    policy: GraphPolicy,
) -> list[Document]:
    """
    Apply history_window to documents.
    A document is retained if its most recent turn_id is within
    the last `policy.history_window` turns.
    """
    window = policy.history_window
    if window <= 0:
        # for the 0 case all docs are from the current turn
        return docs
    
    seen_turns: set[UUID] = set()
    ordered_turns: list[UUID] = []

    for doc in reversed(docs):
        turn_id: UUID | None = doc.metadata.get("turn_id")
        if turn_id is None:
            continue
        if turn_id not in seen_turns:
            seen_turns.add(turn_id)
            ordered_turns.append(turn_id)
        if len(ordered_turns) == window:
            break
    
    keep_turns = set(ordered_turns)

    return [
        doc
        for doc in docs
        if doc.metadata.get("turn_id") in keep_turns
    ]