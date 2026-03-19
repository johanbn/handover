'''Intended to be main access point '''
from fastapi import FastAPI
from ruter_chatbot.specs.app import APP
from ruter_chatbot.orchestrator import Orchestrator
from ruter_chatbot.types.iac.app_spec import AppSpec
# from orchestrator import Orchestrator
# from specs.orchestrator_spec import orch_spec

app = FastAPI()
# security middleware, etc.

@app.get("/")
async def root_info():
    return {
        "message": """
Hei, du har nådd roten av Ruters Chatbot-API for kundeservice.
Besøk samme addressen /docs for mer informasjon om hvordan du kan bruke dette APIet.
"""
}

# endpoints that use the Orchestrator
# NOTE: If this file gets crowded we move app definition to app.py
# If it becomes too crowded yet again we find a way to organize endpoints in
# subdirectories so we can import them here for use.

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

orch = Orchestrator(APP)

@app.get("/app-spec", response_model=AppSpec)
def get_app_spec() -> AppSpec:
    return orch.spec