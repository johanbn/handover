from __future__ import annotations

from typing import Any

from ruter_chatbot.types.iac.node_spec import ConditionalNodeSpec
from ruter_chatbot.types.iac.state_spec import RagState


class ConditionalNode:
    def __init__(self, *, field: str) -> None:
        self.field = field

    @classmethod
    def from_spec(
        cls,
        spec: ConditionalNodeSpec,
        **deps: Any,
    ) -> "ConditionalNode":
        return cls(field=spec.field)

    def route(self, state: RagState) -> str | None:
        value = getattr(state, self.field, None)
        if value is None:
            return None
        return str(value)