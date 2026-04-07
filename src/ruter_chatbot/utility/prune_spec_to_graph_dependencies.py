from __future__ import annotations

from ruter_chatbot.types.iac.app_spec import OrchestratorSpec
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec, RetrieverNodeSpec


def prune_spec_to_graph_dependencies(spec: OrchestratorSpec) -> OrchestratorSpec:
    if not spec.graph:
        raise ValueError(
            "Cannot prune OrchestratorSpec unless it contains a GraphSpec."
        )
    used_models: set[str] = set()
    used_pipelines: set[str] = set()
    used_prompts: set[str] = set()
    used_vector_stores: set[str] = set()

    for node in spec.graph.nodes:
        if isinstance(node, LLMNodeSpec):
            used_pipelines.add(node.pipeline_key)
            used_prompts.add(node.prompt_key)
        elif isinstance(node, RetrieverNodeSpec):
            used_vector_stores.add(node.store_key)

    for pipeline_key in used_pipelines:
        if pipeline_key not in spec.pipelines:
            raise KeyError(f"Unknown pipeline: {pipeline_key}")
        used_models.add(spec.pipelines[pipeline_key].model_key)

    missing_prompts = [key for key in used_prompts if key not in spec.prompts]
    if missing_prompts:
        raise KeyError(f"Unknown prompt(s): {', '.join(sorted(missing_prompts))}")

    missing_vector_stores = [key for key in used_vector_stores if key not in spec.vector_stores]
    if missing_vector_stores:
        raise KeyError(
            f"Unknown vector store(s): {', '.join(sorted(missing_vector_stores))}"
        )

    missing_models = [key for key in used_models if key not in spec.models]
    if missing_models:
        raise KeyError(f"Unknown model(s): {', '.join(sorted(missing_models))}")

    return OrchestratorSpec(
        models={key: spec.models[key] for key in used_models},
        pipelines={key: spec.pipelines[key] for key in used_pipelines},
        prompts={key: spec.prompts[key] for key in used_prompts},
        vector_stores={key: spec.vector_stores[key] for key in used_vector_stores},
        graph=spec.graph,
    )
