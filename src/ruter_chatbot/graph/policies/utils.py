from langchain_core.messages import (
    BaseMessage,
)

def is_context_message(msg: BaseMessage) -> bool:
    """Returns True when the message is a `context` message."""
    kind = getattr(msg, "kind", None) or msg.additional_kwargs.get("kind")
    return kind == "context"
