from __future__ import annotations

from pydantic import BaseModel, Field

from ruter_chatbot.types.iac.graph_spec import GraphSpec
from ruter_chatbot.types.iac.model_spec import ModelSpec
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec


class AppSpec(BaseModel):
    models: dict[str, ModelSpec] = Field(default_factory=dict)
    pipelines: dict[str, PipelineSpec] = Field(default_factory=dict)
    prompts: dict[str, PromptSpec] = Field(default_factory=dict)
    vector_stores: dict[str, VectorStoreSpec] = Field(default_factory=dict)
    graph: GraphSpec