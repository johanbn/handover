from __future__ import annotations

import logging
from uuid import uuid4

import chainlit as cl

from demo_utils import create_demo_orchestrator


GRAPH_KEY = "ruter_tools_demo"
logger = logging.getLogger(__name__)
_ORCH = None


def get_orchestrator():
    global _ORCH

    if _ORCH is None:
        _ORCH = create_demo_orchestrator(
            graph_key=GRAPH_KEY,
            temperature=0.2,
        )

    return _ORCH


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("orch", get_orchestrator())
    cl.user_session.set("conversation_id", str(uuid4()))

    await cl.Message(
        content="Klar. Spør om Ruter, billetter, regler eller reiseruter."
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    orch = cl.user_session.get("orch")
    conv_id = cl.user_session.get("conversation_id")
    question = (message.content or "").strip()

    logger.info("Chainlit on_message received content=%r", message.content)

    if not question:
        logger.warning("Ignoring empty Chainlit message event")
        return

    if orch is None:
        orch = get_orchestrator()
        cl.user_session.set("orch", orch)

    if conv_id is None:
        conv_id = str(uuid4())
        cl.user_session.set("conversation_id", conv_id)

    result = await cl.make_async(orch.ask)(question, conv_id)
    await cl.Message(content=result.answer).send()
