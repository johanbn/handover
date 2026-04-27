from abc import ABC, abstractmethod
from typing import Any

from ruter_chatbot.types.iac.node_spec import NodeSpec
from ruter_chatbot.types.iac.state_spec import RagState


class BaseNode(ABC):
    @classmethod
    @abstractmethod
    def from_spec(cls, spec: Any, **deps: Any):
        raise NotImplementedError

    @abstractmethod
    def __call__(self, state: RagState) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def to_spec(self) -> NodeSpec:
        raise NotImplementedError
