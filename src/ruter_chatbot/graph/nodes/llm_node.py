from __future__ import annotations

from ruter_chatbot.logger import get_logger
from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from ruter_chatbot.graph.nodes.base import BaseNode
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.state_spec import RagState

logger = get_logger(__name__)


def build_context(docs: list[Document], max_chars_per_doc: int = 10_000) -> str:
    if not docs:
        return ""

    parts: list[str] = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        text = doc.page_content.strip()[:max_chars_per_doc]
        parts.append(f"[Doc {i} | source={source}]\n{text}")

    return "\n\n".join(parts)


class LLMNode(BaseNode):
    def __init__(
        self,
        *,
        pipelines: PipelineRegistry,
        prompt_template: str,
        pipeline_key: str,
        output_key: str = "answer",
        include_history: bool = True,
        history_window: int = 5,
    ) -> None:
        self.pipelines = pipelines
        self.prompt_template = prompt_template
        self.pipeline_key = pipeline_key
        self.output_key = output_key
        self.include_history = include_history
        self.history_window = history_window

    @classmethod
    def from_spec(
        cls,
        spec: LLMNodeSpec,
        **deps: Any,
    ) -> "LLMNode":
        prompts: dict[str, PromptSpec] = deps["prompts"]

        if spec.prompt_key not in prompts:
            raise KeyError(f"Unknown prompt key: {spec.prompt_key}")

        return cls(
            pipelines=deps["pipelines"],
            prompt_template=prompts[spec.prompt_key].template,
            pipeline_key=spec.pipeline_key,
            output_key=spec.output_key,
            include_history=spec.include_history,
            history_window=spec.history_window,
        )

    def __call__(self, state: RagState) -> dict[str, Any]:
        llm = self.pipelines.build(self.pipeline_key)
        context = build_context(state.docs)

        prompt_vars = {
            "question": state.question,
            "context": context,
            "answer": state.answer,
            "route": state.route,
        }
        rendered_prompt = self.prompt_template.format(**prompt_vars)

        history = state.messages[-self.history_window:] if self.include_history else []

        llm_messages = [
            *history,
            HumanMessage(content=rendered_prompt),
        ]

        logger.debug("Invoking LLM with %d messages", len(llm_messages))
        
        
        print(llm_messages)
        resp = llm.invoke(llm_messages)

        return {
            "context": context,
            self.output_key: getattr(resp, "content", ""),
            "messages": [resp],  # let add_messages handle merge
        }