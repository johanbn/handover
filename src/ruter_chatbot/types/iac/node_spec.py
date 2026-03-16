from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class BaseNodeSpec(BaseModel):
    name: str  # unique within Graph.
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
    search_type: Literal["similarity", "mmr"] = "similarity"
    fetch_k: int = 20
    lambda_mult: float = 0.5
    output_key: str = "docs"


NodeSpec = Annotated[
    Union[
        LLMNodeSpec,
        RetrieverNodeSpec,
    ],
    Field(discriminator="kind"),
]