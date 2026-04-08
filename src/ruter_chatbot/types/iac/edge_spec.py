from typing import Union

from pydantic import BaseModel

class BaseEdgeSpec(BaseModel):
    source: str

class SimpleEdgeSpec(BaseEdgeSpec):
    target: str

class RouterEdgeSpec(BaseEdgeSpec):
    routes: dict[str, str]  # route_value -> target_node
    default_target: str | None = None
    state_route_field: str = "route"


class ToolsConditionEdgeSpec(BaseEdgeSpec):
    tool_target: str
    no_tool_target: str | None = None


EdgeSpec = Union[
    SimpleEdgeSpec,
    RouterEdgeSpec,
    ToolsConditionEdgeSpec,
]
