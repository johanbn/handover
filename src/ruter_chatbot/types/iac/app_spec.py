from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal

from ruter_chatbot.types.iac.graph_spec import GraphSpec
from ruter_chatbot.types.iac.model_spec import ModelSpec
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec, RetrieverNodeSpec, ToolNodeSpec
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.tool_spec import ToolSpec
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec

SpecKind = Literal["models", "pipelines", "prompts", "tools", "vector_stores"]

class OrchestratorSpec(BaseModel):
    models: dict[str, ModelSpec] = Field(default_factory=dict)
    pipelines: dict[str, PipelineSpec] = Field(default_factory=dict)
    prompts: dict[str, PromptSpec] = Field(default_factory=dict)
    tools: dict[str, ToolSpec] = Field(default_factory=dict)
    vector_stores: dict[str, VectorStoreSpec] = Field(default_factory=dict)
    graph: GraphSpec | None = Field(default=None)

    def pruned_to_graph(self) -> "OrchestratorSpec":
        if not self.graph:
            raise ValueError(
                "Cannot prune OrchestratorSpec unless it contains a GraphSpec."
            )

        used_models: set[str] = set()
        used_pipelines: set[str] = set()
        used_prompts: set[str] = set()
        used_tools: set[str] = set()
        used_vector_stores: set[str] = set()

        for node in self.graph.nodes:
            if isinstance(node, LLMNodeSpec):
                used_pipelines.add(node.pipeline_key)
                used_prompts.add(node.prompt_key)
                used_tools.update(node.tool_keys)
            elif isinstance(node, ToolNodeSpec):
                used_tools.update(node.tool_keys)
            elif isinstance(node, RetrieverNodeSpec):
                used_vector_stores.add(node.store_key)

        for pipeline_key in used_pipelines:
            if pipeline_key not in self.pipelines:
                raise KeyError(f"Unknown pipeline: {pipeline_key}")
            used_models.add(self.pipelines[pipeline_key].model_key)

        missing_tools = [key for key in used_tools if key not in self.tools]
        if missing_tools:
            raise KeyError(f"Unknown tool(s): {', '.join(sorted(missing_tools))}")

        for tool_key in used_tools:
            store_key = self.tools[tool_key].args.get("store_key")
            if isinstance(store_key, str) and store_key:
                used_vector_stores.add(store_key)

        missing_prompts = [key for key in used_prompts if key not in self.prompts]
        if missing_prompts:
            raise KeyError(f"Unknown prompt(s): {', '.join(sorted(missing_prompts))}")

        missing_vector_stores = [
            key for key in used_vector_stores if key not in self.vector_stores
        ]
        if missing_vector_stores:
            raise KeyError(
                f"Unknown vector store(s): {', '.join(sorted(missing_vector_stores))}"
            )

        missing_models = [key for key in used_models if key not in self.models]
        if missing_models:
            raise KeyError(f"Unknown model(s): {', '.join(sorted(missing_models))}")

        return OrchestratorSpec(
            models={
                key: self.models[key].model_copy(deep=True)
                for key in sorted(used_models)
            },
            pipelines={
                key: self.pipelines[key].model_copy(deep=True)
                for key in sorted(used_pipelines)
            },
            prompts={
                key: self.prompts[key].model_copy(deep=True)
                for key in sorted(used_prompts)
            },
            tools={
                key: self.tools[key].model_copy(deep=True)
                for key in sorted(used_tools)
            },
            vector_stores={
                key: self.vector_stores[key].model_copy(deep=True)
                for key in sorted(used_vector_stores)
            },
            graph=self.graph.model_copy(deep=True),
        )


AppSpec = OrchestratorSpec
