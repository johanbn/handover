from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class BaseNodeSpec(BaseModel):
    name: str  # unique within Graph.
    output_key: str | None = None


class LLMNodeSpec(BaseNodeSpec):
    kind: Literal["llm"]
    pipeline_key: str
    prompt_key: str
    tool_keys: list[str] = Field(default_factory=list)
    include_history: bool = True
    history_window: int = 5
    output_key: str = "answer"


class RetrieverNodeSpec(BaseNodeSpec):
    kind: Literal["retriever"]
    store_key: str
    search_type: Literal[
        "similarity",
        "scored_similarity",
        "mmr",
    ] = "mmr"
    top_k: int = 5
    fetch_k: int = 20
    lambda_mult: float = 0.5
    output_key: str = "docs"


class ToolNodeSpec(BaseNodeSpec):
    kind: Literal["tool"]
    tool_keys: list[str] = Field(default_factory=list)


NodeSpec = Annotated[
    Union[
        LLMNodeSpec,
        RetrieverNodeSpec,
        ToolNodeSpec,
    ],
    Field(discriminator="kind"),
]
