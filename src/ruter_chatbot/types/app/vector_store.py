from typing import Any
from pydantic import BaseModel, Field


class VectorStoreInfo(BaseModel):
    name: str
    state: str


class VectorStoreListResponse(BaseModel):
    stores: list[VectorStoreInfo]


class SimilaritySearchRequest(BaseModel):
    store_name: str
    query: str
    k: int = 4
    with_score: bool = False


class MmrSearchRequest(BaseModel):
    store_name: str
    query: str
    k: int = 4
    fetch_k: int = 20
    lambda_mult: float = 0.5


class VectorStoreSearchHit(BaseModel):
    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class VectorStoreSearchResponse(BaseModel):
    store_name: str
    query: str
    k: int
    hits: list[VectorStoreSearchHit]


class InitializeVectorStoresRequest(BaseModel):
    store_keys: list[str] = Field(default_factory=list)


class InitializeVectorStoresResponse(BaseModel):
    status: str