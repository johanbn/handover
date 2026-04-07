'''
Provides function:
    get_answer_from_state:
        Reads `answer` from state if it exists.
        Falls back to last AIMessage in `messages` if not.
        Defaults to "I couldn't answer the question." if all else fails.
        Supports pydantic models and dictionaries.
'''
from typing import Any
from langchain_core.messages import AIMessage

from ruter_chatbot.types.app.ask import AskState
from ruter_chatbot.utility.get_last_state_message import get_last_state_message


def get_answer_from_state(state: AskState | dict[str, Any]) -> str:
    '''
    Reads `answer` from state if it exists.
    Falls back to last AIMessage in `messages` if not.
    Defaults to "I couldn't answer the question." if all else fails.
    Supports pydantic models and dictionaries.
    '''
    fallback = "I couldn't answer the question."
    message = None

    answer = (
        state.get("answer")
        if isinstance(state, dict)
        else getattr(state, "answer", None)
    )
    if not answer:
        message = get_last_state_message(state, target_type=AIMessage)

    answer = answer or message or fallback
    if isinstance(answer, str):
        return answer

    return getattr(answer, "text", fallback)