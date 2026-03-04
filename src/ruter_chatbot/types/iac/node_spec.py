from pydantic import BaseModel, Field
from typing import Literal, Annotated, Union

class BaseNodeSpec(BaseModel):
    # all variants need a kind
    name: str # unique within Graph.
    output_key: str | None = None

class LLMNodeSpec(BaseNodeSpec):
    kind: Literal["llm"]
    model_key: str # key to model registry
    prompt_key: str # key to prompt registry
    include_history: bool = True # Not sure we want this here... but maybe?
    history_window: int = 5 # tied to the above
    output_key: str = "answer" # key in Graph State

class RetrieverNodeSpec(BaseNodeSpec):
    kind: Literal["retriever"]
    store_key: str # key to Vector Store registry
    top_k: int = 5
    output_key: str = "docs"

NodeSpec = Annotated[
    Union[
        LLMNodeSpec, RetrieverNodeSpec
    ], Field(discriminator="kind")
]
