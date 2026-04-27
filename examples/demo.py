from demo_utils import (
    create_demo_orchestrator,
    draw_graph_png,
)


# Available graphs:
# - "conditional_demo"
# - "aws_demo"
# - "ruter_tools_demo"


def main() -> None:
    orch = create_demo_orchestrator(
        graph_key="ruter_tools_demo",
        temperature=0.2,
        init_store_key=None,
    )
    graph = orch.graph
    print(orch.to_spec().model_dump_json(indent=4))

    draw_graph_png(graph, "graph.png")
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
