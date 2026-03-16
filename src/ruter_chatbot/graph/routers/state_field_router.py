from __future__ import annotations

from ruter_chatbot.types.iac.state_spec import RagState


class StateFieldRouter:
    def __init__(self, *, field: str) -> None:
        self.field = field

    def route(self, state: RagState) -> str | None:
        value = getattr(state, self.field, None)
        if value is None:
            return None
        return str(value)