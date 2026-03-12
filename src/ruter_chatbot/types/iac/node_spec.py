from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class BaseNodeSpec(BaseModel):
    name: str
    output_key: str | None = None


class LLMNodeSpec(BaseNodeSpec):
    kind: Literal["llm"]
    pipeline_key: str
    prompt_key: str
    include_history: bool = True
    history_window: int = 5
    output_key: str = "answer"


class RetrieverNodeSpec(BaseNodeSpec):
    kind: Literal["retriever"]
    store_key: str
    top_k: int = 5
    with_score: bool = False
    output_key: str = "docs"


class ConditionalNodeSpec(BaseNodeSpec):
    kind: Literal["conditional"]
    field: str


NodeSpec = Annotated[
    Union[
        LLMNodeSpec,
        RetrieverNodeSpec,
        ConditionalNodeSpec,
    ],
    Field(discriminator="kind"),
]