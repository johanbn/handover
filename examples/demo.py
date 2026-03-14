import asyncio
import os

from ruter_chatbot.orchestrator import Orchestrator

from ruter_chatbot.types.iac.app_spec import AppSpec

from ruter_chatbot.specs.prompts import PROMPTS
from ruter_chatbot.specs.models import MODELS
from ruter_chatbot.specs.pipelines import PIPELINES
from ruter_chatbot.specs.vector_stores import VECTOR_STORES
from ruter_chatbot.specs.graphs import GRAPH


def draw_graph_png(graph, file_path: str = "graph.png") -> None:
    import sys

    try:
        g = graph.get_graph(xray=True)
        png_bytes = g.draw_mermaid_png()

        with open(file_path, "wb") as f:
            f.write(png_bytes)

        print(f"\nGraph visualization saved to: {file_path}")

        if sys.platform.startswith("win"):
            os.startfile(file_path)

    except Exception as e:
        print("\nCould not render graph visualization.")
        print("Error:", e)



APP = AppSpec(
    models=MODELS,
    pipelines=PIPELINES,
    prompts=PROMPTS,
    vector_stores=VECTOR_STORES,
    graph=GRAPH["conditional_demo"] # aws_demo, conditional_demo, demo
)

async def main() -> None:
    # example of changing parameter to APP.

    APP.pipelines["qwen_small_precise"].args["temperature"] = 0.7
    #APP.vector_stores["ruter_store"].chunker.max_chunk_size = 800
    print(APP.model_dump_json(indent=4))
    
    orch = Orchestrator(APP)
    draw_graph_png(orch.graph, "graph.png")


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