from pydantic import BaseModel

from ruter_chatbot.types.iac.model_spec import ModelSpec
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.types.iac.graph_spec import GraphSpec


class AppSpec(BaseModel):
    models: list[ModelSpec] = []
    pipelines: list[PipelineSpec] = []
    prompts: list[PromptSpec] = []
    vector_stores: list[VectorStoreSpec] = []
    graph: GraphSpec