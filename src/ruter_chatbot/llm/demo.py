from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel, Field

from ruter_chatbot.llm.model import ModelRegistry
from ruter_chatbot.llm.pipeline import PipelineRegistry
from ruter_chatbot.llm.specs import ModelSpec, NodeSpec, PipelineSpec

# This file will be deleted in the future since it not exact how the future is.

class NodeSpec(BaseModel):
    key: str
    pipeline_key: str
    args: Dict[str, Any] = Field(default_factory=dict)

class NodeRegistry:
    def __init__(self, pipeline_registry: PipelineRegistry):
        self.pipeline_registry = pipeline_registry
        self.nodes: Dict[str, NodeSpec] = {}

    def from_spec(self, spec: NodeSpec) -> None:
        self.nodes[spec.key] = spec

    def invoke(self, node_key: str, **kwargs: Any) -> Any:
        if node_key not in self.nodes:
            raise KeyError(f"Unknown node key: {node_key}")

        node = self.nodes[node_key]
        llm = self.pipeline_registry.build(node.pipeline_key)
        prompt = node.args["prompt_template"].format(**kwargs)

        return llm.invoke(prompt)


class Orchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.models = ModelRegistry()
        self.pipelines = PipelineRegistry(self.models)
        self.nodes = NodeRegistry(self.pipelines)

        for item in config.get("models", []):
            self.models.from_spec(ModelSpec(**item))

        for item in config.get("pipelines", []):
            self.pipelines.from_spec(PipelineSpec(**item))

        for item in config.get("nodes", []):
            self.nodes.from_spec(NodeSpec(**item))

    def invoke_node(self, node_key: str, **kwargs: Any) -> Any:
        return self.nodes.invoke(node_key, **kwargs)


CONFIG = {
    "models": [
        {
            "key": "qwen",
            "type": "ollama_model",
            "args": {
                "model": "qwen2.5:3b",
                "temperature": 0.2,
            },
        },
    ],
    "pipelines": [
        {
            "key": "creative",
            "type": "ollama_pipeline",
            "model_key": "qwen",
            "args": {
                "temperature": 0.9,
            },
        },
        {
            "key": "precise",
            "type": "ollama_pipeline",
            "model_key": "qwen",
            "args": {},
        },
    ],
    "nodes": [
        {
            "key": "summary_node",
            "pipeline_key": "precise",
            "args": {
                "prompt_template": "Summarize in one sentence:\n\n{text}",
            },
        },
        {
            "key": "story_node",
            "pipeline_key": "creative",
            "args": {
                "prompt_template": "Write creatively about:\n\n{text}",
            },
        },
    ],
}


if __name__ == "__main__":
    orch = Orchestrator(CONFIG)

    print("=== summary_node ===")
    result = orch.invoke_node(
        "summary_node",
        text="Large language models predict likely next tokens.",
    )
    print(result.content)

    orch.pipelines.update("creative", temperature=0.4)

    print("\n=== story_node ===")
    result = orch.invoke_node(
        "story_node",
        text="A robot learning to speak with humans.",
    )
    print(result.content)