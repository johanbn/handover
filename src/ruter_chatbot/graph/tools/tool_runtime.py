from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, ClassVar

from ruter_chatbot.graph.tools.ruter_tools import (
    build_get_ruter_departures_tool,
    build_lookup_ruter_line_tool,
    build_plan_ruter_journey_tool,
    build_request_docs_tool,
    build_search_ruter_stops_tool,
)
from ruter_chatbot.types.iac.tool_spec import ToolSpec
from ruter_chatbot.types.keyed import Keyed
from ruter_chatbot.types.spec_based import SpecBased

if TYPE_CHECKING:
    from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry


class ToolRuntime(SpecBased[ToolSpec], Keyed):
    spec_class = ToolSpec
    BUILDERS: ClassVar[dict[str, Callable[[ToolSpec, "VectorStoreRegistry | None"], Any]]] = {
        "search_ruter_stops": lambda spec: build_search_ruter_stops_tool(
            client_name=spec.args.get("client_name")
        ),
        "get_ruter_departures": lambda spec: build_get_ruter_departures_tool(
            client_name=spec.args.get("client_name")
        ),
        "plan_ruter_journey": lambda spec: build_plan_ruter_journey_tool(
            client_name=spec.args.get("client_name")
        ),
        "lookup_ruter_line": lambda spec: build_lookup_ruter_line_tool(
            client_name=spec.args.get("client_name")
        ),
        "request_docs": lambda _spec: build_request_docs_tool(),
    }

    def __init__(self, *, spec: ToolSpec, tool: Any) -> None:
        self._spec = spec
        self._tool = tool

    @classmethod
    def from_spec(cls, spec: ToolSpec) -> "ToolRuntime":
        spec_obj = ToolSpec.model_validate(spec)

        if spec_obj.type != "builtin":
            raise ValueError(f"Unsupported tool type: {spec_obj.type}")

        try:
            builder = cls.BUILDERS[spec_obj.key]
        except KeyError as exc:
            raise KeyError(f"Unknown builtin tool: {spec_obj.key}") from exc

        return cls(spec=spec_obj, tool=builder(spec_obj))

    def to_spec(self) -> ToolSpec:
        return self._spec.model_copy(deep=True)

    @property
    def key(self) -> str:
        return self._spec.key

    def build(self) -> Any:
        return self._tool
