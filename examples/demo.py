import os

from ruter_chatbot.orchestrator import Orchestrator
from ruter_chatbot.types.iac.app_spec import OrchestratorSpec

from ruter_chatbot.specs.prompts import PROMPTS
from ruter_chatbot.specs.models import MODELS
from ruter_chatbot.specs.pipelines import PIPELINES
from ruter_chatbot.specs.tools import TOOLS
from ruter_chatbot.specs.vector_stores import VECTOR_STORES
from ruter_chatbot.specs.graphs import GRAPHS

# Available graphs:
# - "conditional_demo"
# - "aws_demo"
# - "ruter_tools_demo"


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


APP = OrchestratorSpec(
    models=MODELS,
    pipelines=PIPELINES,
    prompts=PROMPTS,
    tools=TOOLS,
    vector_stores=VECTOR_STORES,
    graph=GRAPHS["aws_demo"],
)


def main() -> None:
    app = APP.model_copy(deep=True)
    app.pipelines["claude_bedrock_rag"].args["temperature"] = 0.2

    orch = Orchestrator.from_spec(app)

    graph = orch.build_graph()
    #print(orch.to_spec().model_dump_json(indent=4))

    draw_graph_png(graph, "graph.png")

    print("Initializing vector stores...")
    orch.initialize("ruter_store_aws_extern", "ruter_store_aws_intern")

    print("\nUsed spec after vector store init:")
    #print(orch.to_used_spec().model_dump_json(indent=4))
    print("Ready.\n")

    conv_id = "1"

    while True:
        q = input("You: ").strip()

        if not q:
            continue

        if q.lower() in {"exit", "quit"}:
            break

        result = orch.ask(q, conv_id)
        print("\nAssistant:", result.answer)
        print("")


if __name__ == "__main__":
    main()
