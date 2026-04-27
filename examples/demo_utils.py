from __future__ import annotations

import os
import sys
from pathlib import Path

import mlflow

from ruter_chatbot.orchestrator import Orchestrator
from ruter_chatbot.specs.graphs import GRAPHS
from ruter_chatbot.specs.models import MODELS
from ruter_chatbot.specs.pipelines import PIPELINES
from ruter_chatbot.specs.prompts import PROMPTS
from ruter_chatbot.specs.tools import TOOLS
from ruter_chatbot.specs.vector_stores import VECTOR_STORES
from ruter_chatbot.types.iac.app_spec import OrchestratorSpec


DEFAULT_GRAPH_KEY = "ruter_tools_demo"


def build_demo_app(graph_key: str = DEFAULT_GRAPH_KEY) -> OrchestratorSpec:
    return OrchestratorSpec(
        models=MODELS,
        pipelines=PIPELINES,
        prompts=PROMPTS,
        tools=TOOLS,
        vector_stores=VECTOR_STORES,
        graph=GRAPHS[graph_key],
    )


def setup_mlflow() -> None:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "ruter_chatbot_demo")

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    mlflow.langchain.autolog()

    print(f"MLflow tracing enabled for experiment: {experiment_name}")
    print(f"MLflow tracking URI: {tracking_uri}")


def log_used_spec_to_mlflow(orch: Orchestrator) -> None:
    used_spec = orch.to_spec().pruned_to_graph()
    mlflow.log_text(
        used_spec.model_dump_json(indent=2),
        "used_orchestrator_spec.json",
    )


def create_demo_orchestrator(
    *,
    graph_key: str = DEFAULT_GRAPH_KEY,
    temperature: float = 0.2,
    init_store_key: str | None = None,
) -> Orchestrator:
    setup_mlflow()

    app = build_demo_app(graph_key).model_copy(deep=True)
    app.pipelines["claude_bedrock_rag"].args["temperature"] = temperature
    app = app.pruned_to_graph()

    orch = Orchestrator.from_spec(app)
    log_used_spec_to_mlflow(orch)
    orch.build_graph()

    if init_store_key:
        orch.initialize(init_store_key)
    elif orch.vector_stores:
        orch.initialize(*tuple(orch.vector_stores.keys()))

    return orch


def draw_graph_png(graph, file_path: str = "graph.png") -> None:
    try:
        g = graph.get_graph(xray=True)
        png_bytes = g.draw_mermaid_png()

        with open(file_path, "wb") as f:
            f.write(png_bytes)

        print(f"\nGraph visualization saved to: {file_path}")

        if sys.platform.startswith("win"):
            os.startfile(file_path)

    except Exception as exc:
        print("\nCould not render graph visualization.")
        print("Error:", exc)


def resolve_graph_image_path(file_name: str = "graph.png") -> Path:
    return Path(file_name).resolve()
