from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class BaseRouterSpec(BaseModel):
    name: str  # unique within Graph.


class StateFieldRouterSpec(BaseRouterSpec):
    kind: Literal["state_field"]
    field: str


RouterSpec = Annotated[
    Union[
        StateFieldRouterSpec,
    ],
    Field(discriminator="kind"),
]