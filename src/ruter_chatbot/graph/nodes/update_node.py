from __future__ import annotations
from typing import Any

from langgraph.types import Command

from ruter_chatbot.graph.nodes.base import BaseNode
from ruter_chatbot.types.iac.node_spec import UpdateNodeSpec

class UpdateNode(BaseNode):
    '''
    Updates state fields with specified values, allowing for state control.
    '''
    def __init__(
        self,
        *,
        name: str,
        updates: dict[str, Any],
    ):
        self.name = name
        self.updates = dict(updates)
    
    @classmethod
    def from_spec(cls, spec: UpdateNodeSpec) -> "UpdateNode":
        return cls(
            name=spec.name,
            updates=dict(spec.updates)
        )

    def to_spec(self) -> UpdateNodeSpec:
        return UpdateNodeSpec(
            kind="update",
            name=self.name,
            updates=dict(self.updates),
        )
    
    def __call__(self, _state) -> dict[str, Any]:
        return Command(
            update=dict(self.updates)
        )