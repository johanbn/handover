from typing import Any
from pydantic import BaseModel, Field

from langchain_core.documents import Document

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

    @classmethod
    def from_doc(
        cls,
        maybe_scored_doc: Document | tuple[Document, float]
    ) -> "VectorStoreSearchHit":
        '''
        Converts a Document or a tuple of Document and float into a VectorStoreSearchHit
        Floats are interpreted as a scores.
        '''
        if isinstance(maybe_scored_doc, tuple):
            doc, score = maybe_scored_doc
        else:
            doc, score = maybe_scored_doc, None

        return cls(
            page_content=doc.page_content,
            metadata=dict(doc.metadata),
            score=score,
        )

    @classmethod
    def from_doc_list(
        cls,
        maybe_scored_docs: list[Document | tuple[Document, float]]
    ) -> list["VectorStoreSearchHit"]:
        '''
        Converts a list of Documents or tuples of Documents and floats into VectorStoreSearchHits.
        Floats are interpreted as scores.
        '''
        return [
            cls.from_doc(maybe_scored_doc)
            for maybe_scored_doc in maybe_scored_docs
        ]

class VectorStoreSearchResponse(BaseModel):
    store_name: str
    query: str
    k: int
    hits: list[VectorStoreSearchHit]


class InitializeVectorStoresRequest(BaseModel):
    store_keys: list[str] = Field(default_factory=list)


class InitializeVectorStoresResponse(BaseModel):
    status: str