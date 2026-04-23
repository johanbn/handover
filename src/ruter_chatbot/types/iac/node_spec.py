from typing import Annotated, Literal, Union, Any

from pydantic import BaseModel, Field


class BaseNodeSpec(BaseModel):
    name: str  # unique within Graph.
    output_key: str | None = None

class LLMNodeSpec(BaseNodeSpec):
    '''
    Uses an LLM from pipeline_key with a prompt from prompt_key to generate output to state.output_key.
    Binds tools from tool_keys.
    '''
    kind: Literal["llm"]
    pipeline_key: str
    prompt_key: str
    tool_keys: list[str] = Field(default_factory=list)
    output_key: str = "answer"

class RetrieverNodeSpec(BaseNodeSpec):
    '''
    Retrieves documents from store at store_key using search type from search_type.
    Stores found documents at state.output_key.
    '''
    kind: Literal["retriever"]
    store_key: str
    search_type: Literal[
        "similarity",
        "scored_similarity",
        "mmr",
    ] = "mmr"
    top_k: int = 5
    fetch_k: int = 20
    '''Only relevant for search_type "mmr"'''
    lambda_mult: float = 0.5
    output_key: str = "docs"

class UpdateNodeSpec(BaseNodeSpec):
    '''
    Updates state fields with specified values, allowing for state control.
    '''
    kind: Literal["update"]
    updates: dict[str, Any] = Field(default_factory=dict)
    '''The fields the node will update and what it will update them with.'''


class ToolNodeSpec(BaseNodeSpec):
    '''
    Executes tools from tool_keys based on requests from preceding LLMNode.
    '''
    kind: Literal["tool"]
    tool_keys: list[str] = Field(default_factory=list)


NodeSpec = Annotated[
    Union[
        LLMNodeSpec,
        RetrieverNodeSpec,
        UpdateNodeSpec,
        ToolNodeSpec,
    ],
    Field(discriminator="kind"),
]
