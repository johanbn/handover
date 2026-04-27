from __future__ import annotations

from uuid import uuid4

import chainlit as cl

from ruter_chatbot.logger import get_logger
from ruter_chatbot.orchestrator import Orchestrator
from ruter_chatbot.specs.app import APP

logger = get_logger(__name__)

# Mirror the API runtime style exactly so Chainlit uses the same graph as API.
orch = Orchestrator.from_spec(APP.pruned_to_graph())
orch.initialize()


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("conversation_id", str(uuid4()))

    await cl.Message(
        content=(
            "Dette er en midlertidig demo for Kundeservice. Denne versjonen av "
            "chatbotten har tilgang på informasjon fra RuterWiki som er tagget "
            "for chatbot (cb-intern eller cb-ekstern). Den er tilgjengelig så "
            "dere skal kunne prøve hvordan den fungerer i praksis. Den vil "
            "erstattes av spesialiserte versjoner for Ruters apper etterhvert "
            "som de utvikles internt. Dersom chatbotten gjør feil i testfasen "
            "bør det formidles tilbake til oss som utvikler den for dere hos "
            "Unicus(johan.norlinder@ruter.no eller trygve.taranger@ruter.no)." 
            "Spør i vei!"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    conversation_id = cl.user_session.get("conversation_id")
    question = (message.content or "").strip()

    logger.info("Chainlit on_message received content=%r", message.content)

    if not question:
        logger.warning("Ignoring empty Chainlit message event")
        return

    if conversation_id is None:
        conversation_id = str(uuid4())
        cl.user_session.set("conversation_id", conversation_id)

    result = await cl.make_async(orch.ask)(
        question=question,
        conversation_id=conversation_id,
    )
    await cl.Message(content=result.answer).send()
