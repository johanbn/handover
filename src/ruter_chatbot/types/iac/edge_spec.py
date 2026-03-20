from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

class BaseEdgeSpec(BaseModel):
    source: str

class SimpleEdgeSpec(BaseEdgeSpec):
    kind: Literal["simple"]
    target: str

class RouterEdgeSpec(BaseEdgeSpec):
    kind: Literal["router"]
    routes: dict[str, str]  # route_value -> target_node
    default_target: str | None = None
    state_route_field: str = "route"

EdgeSpec = Annotated[
    Union[
        SimpleEdgeSpec,
        RouterEdgeSpec,
    ],
    Field(discriminator="kind")
]
