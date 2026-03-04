from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated

class BaseEdgeSpec(BaseModel):
    kind: str
    source: str

class SimpleEdgeSpec(BaseEdgeSpec):
    kind: Literal["simple"]
    target: str

class RouterEdgeSpec(BaseEdgeSpec):
    kind: Literal["router"]
    router_key: str
    routes: dict[str, str] # output_value -> target_node
    default_target: str | None = None

EdgeSpec = Annotated[
    Union[
        SimpleEdgeSpec,
        RouterEdgeSpec
    ], Field(discriminator="kind"),
]
