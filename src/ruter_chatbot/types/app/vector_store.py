from typing import Any, Literal
from pydantic import BaseModel, Field


class VectorStoreInfo(BaseModel):
    name: str
    state: str


class VectorStoreListResponse(BaseModel):
    stores: list[VectorStoreInfo]


class VectorStoreSearchRequest(BaseModel):
    store_name: str
    query: str
    method: Literal["similarity", "mmr"] = "similarity"
    k: int = 4
    with_score: bool = False
    fetch_k: int = 20
    lambda_mult: float = 0.5


class VectorStoreSearchHit(BaseModel):
    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class VectorStoreSearchResponse(BaseModel):
    store_name: str
    method: Literal["similarity", "mmr"]
    query: str
    k: int
    hits: list[VectorStoreSearchHit]


class InitializeVectorStoresRequest(BaseModel):
    store_keys: list[str] = []


class InitializeVectorStoresResponse(BaseModel):
    status: str