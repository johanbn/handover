'''Intended to be main access point '''
from fastapi import FastAPI

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
