from __future__ import annotations

from ruter_chatbot.graph.nodes.llm_node import LLMNode
from ruter_chatbot.graph.nodes.retrieval_node import RetrievalNode
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.iac.node_spec import (
    LLMNodeSpec,
    RetrieverNodeSpec,
    NodeSpec
)
from ruter_chatbot.types.iac.prompt_spec import PromptSpec


class NodeBuilder:
    def __init__(
            self,
            pipelines: PipelineRegistry,
            vector_stores: VectorStoreRegistry,
            prompts: dict[str, PromptSpec]
        ) -> None:
        self.pipelines = pipelines
        self.vector_stores = vector_stores
        self.prompts = prompts

    def from_spec(self, spec: NodeSpec) -> None:
        if isinstance(spec, LLMNodeSpec):
            return LLMNode.from_spec(
                spec,
                pipelines=self.pipelines,
                prompts=self.prompts
            )

        elif isinstance(spec, RetrieverNodeSpec):
            return RetrievalNode.from_spec(
                spec,
                vector_stores=self.vector_stores
            )
        else:
            raise TypeError(f"Unsupported node spec type: {type(spec).__name__}")

