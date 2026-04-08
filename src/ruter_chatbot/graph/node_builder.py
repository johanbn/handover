from __future__ import annotations

from langgraph.prebuilt import ToolNode

from ruter_chatbot.graph.nodes.llm_node import LLMNode
from ruter_chatbot.graph.nodes.retrieval_node import RetrievalNode
from ruter_chatbot.graph.tools.tool_registry import ToolRegistry
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.iac.node_spec import (
    LLMNodeSpec,
    ToolNodeSpec,
    RetrieverNodeSpec,
    NodeSpec,
)
from ruter_chatbot.types.iac.prompt_spec import PromptSpec


class NodeBuilder:
    def __init__(
        self,
        pipelines: PipelineRegistry,
        vector_stores: VectorStoreRegistry,
        prompts: dict[str, PromptSpec],
        tools: ToolRegistry,
    ) -> None:
        self.pipelines = pipelines
        self.vector_stores = vector_stores
        self.prompts = prompts
        self.tools = tools

    def from_spec(self, spec: NodeSpec) -> None:
        if isinstance(spec, LLMNodeSpec):
            return LLMNode.from_spec(
                spec,
                pipelines=self.pipelines,
                prompts=self.prompts,
                tools_registry=self.tools,
            )

        elif isinstance(spec, RetrieverNodeSpec):
            return RetrievalNode.from_spec(
                spec,
                vector_stores=self.vector_stores,
            )
        elif isinstance(spec, ToolNodeSpec):
            return ToolNode(self.tools.get_many(spec.tool_keys))
        else:
            raise TypeError(f"Unsupported node spec type: {type(spec).__name__}")

