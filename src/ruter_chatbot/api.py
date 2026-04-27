'''Intended to be main access point '''
from fastapi import FastAPI

from ruter_chatbot.orchestrator import Orchestrator
from ruter_chatbot.specs.app import APP
from ruter_chatbot.types.app.ask import AskRequest, AskResponse
from ruter_chatbot.types.app.vector_store import (
    MmrSearchRequest,
    SimilaritySearchRequest,
    VectorStoreListResponse,
    VectorStoreSearchResponse,
)
from ruter_chatbot.types.iac.app_spec import AppSpec

api = FastAPI()
# security middleware, etc.

orch = Orchestrator.from_spec(APP.pruned_to_graph())
orch.initialize()
orch.start_daily_vector_store_refreshes(
    start_hour=2,
    start_minute=0,
    stagger_by={"minutes": 30}
)

@api.get("/")
async def root_info():
    return {
        "message": """
Hei, du har nådd roten av Ruters Chatbot-API for kundeservice.
Besøk samme addressen /docs for mer informasjon om hvordan du kan bruke dette APIet.
"""
    }


# endpoints that use the Orchestrator
@api.get("/app-spec", response_model=AppSpec)
def get_app_spec() -> AppSpec:
    return orch.to_spec()


@api.get("/vector-stores", response_model=VectorStoreListResponse)
def list_vector_stores() -> VectorStoreListResponse:
    return orch.list_vector_stores()


@api.post("/vector-stores/search/similarity", response_model=VectorStoreSearchResponse)
def search_vector_store_similarity(
    req: SimilaritySearchRequest,
) -> VectorStoreSearchResponse:
    return orch.search_vector_store_similarity(req)


@api.post("/vector-stores/search/mmr", response_model=VectorStoreSearchResponse)
def search_vector_store_mmr(
    req: MmrSearchRequest,
) -> VectorStoreSearchResponse:
    return orch.search_vector_store_mmr(req)


@api.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    return orch.ask(
        question=req.question,
        conversation_id=req.conversation_id,
        debug=req.debug,
    )
