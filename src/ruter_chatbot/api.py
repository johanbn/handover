'''Intended to be main access point '''
from fastapi import FastAPI

from ruter_chatbot.orchestrator import Orchestrator
from ruter_chatbot.specs.app import APP
from ruter_chatbot.types.app.ask import AskRequest, AskResponse
from ruter_chatbot.types.app.vector_store import (
    InitializeVectorStoresRequest,
    InitializeVectorStoresResponse,
    VectorStoreListResponse,
    VectorStoreSearchRequest,
    VectorStoreSearchResponse,
)
from ruter_chatbot.types.iac.app_spec import AppSpec

app = FastAPI()
# security middleware, etc.

orch = Orchestrator(APP)
#orch.initialize("ruter_store_aws")


@app.get("/")
async def root_info():
    return {
        "message": """
Hei, du har nådd roten av Ruters Chatbot-API for kundeservice.
Besøk samme addressen /docs for mer informasjon om hvordan du kan bruke dette APIet.
"""
    }


@app.get("/confluence_test")
async def confluence_test():
    """Imports BaseProvider to initialize a spec for ConfluenceProvider and return a random Source & its Documents."""
    from random import randint
    from ruter_chatbot.stores.providers.base_provider import BaseProvider
    from ruter_chatbot.specs.providers import ruterwiki_ks_intern

    provider = BaseProvider.from_spec(ruterwiki_ks_intern)
    sources = provider.list_sources()
    if not sources:
        return {"error": "Could not find any sources."}

    source = sources[randint(0, len(sources))]
    docs = provider.get_docs_from_source(source)
    return {
        "source": source,
        "docs": docs
    }


@app.get("/app-spec", response_model=AppSpec)
def get_app_spec() -> AppSpec:
    return orch.spec

@app.get("/vector-stores", response_model=VectorStoreListResponse)
def list_vector_stores() -> VectorStoreListResponse:
    return orch.list_vector_stores()


@app.post("/vector-stores/search", response_model=VectorStoreSearchResponse)
def search_vector_store(
    req: VectorStoreSearchRequest,
) -> VectorStoreSearchResponse:
    return orch.search_vector_store(
        store_name=req.store_name,
        query=req.query,
        method=req.method,
        k=req.k,
        with_score=req.with_score,
        fetch_k=req.fetch_k,
        lambda_mult=req.lambda_mult,
    )


@app.post("/vector-stores/initialize")
def initialize_vector_stores(req: InitializeVectorStoresRequest) -> dict[str, str]:
    if req.store_keys:
        orch.initialize(*req.store_keys)
    else:
        orch.initialize()

    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    return orch.ask(
        question=req.question,
        conversation_id=req.conversation_id,
        debug=req.debug,
    )