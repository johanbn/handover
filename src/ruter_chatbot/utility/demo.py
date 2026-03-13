import asyncio

from ruter_chatbot.orchestrator import Orchestrator

from ruter_chatbot.types.iac.app_spec import AppSpec

from ruter_chatbot.specs.prompts import PROMPTS
from ruter_chatbot.specs.models import MODELS
from ruter_chatbot.specs.pipelines import PIPELINES
from ruter_chatbot.specs.vector_stores import VECTOR_STORES
from ruter_chatbot.specs.graphs import GRAPH

APP = AppSpec(
    models=MODELS,
    pipelines=PIPELINES,
    prompts=PROMPTS,
    vector_stores=VECTOR_STORES,
    graph=GRAPH["demo"]
)

async def main() -> None:
    # example of changing parameter to APP.
    APP.pipelines["qwen_small_precise"].args["temperature"] = 0.7
    APP.vector_stores["ruter_store"].chunker.max_chunk_size = 800
    orch = Orchestrator(APP)

    print("Initializing vector stores...")
    await orch.initialize()
    print("Ready.\n")

    while True:
        q = input("You: ").strip()

        if not q:
            continue

        if q.lower() in {"exit", "quit"}:
            break

        answer = await orch.ask(q)
        print("\nAssistant:", answer)
        print("")


if __name__ == "__main__":
    asyncio.run(main())