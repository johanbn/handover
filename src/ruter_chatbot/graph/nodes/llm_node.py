from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from ruter_chatbot.graph.nodes.base import BaseNode
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.logger import get_logger
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.state_spec import RagState
from ruter_chatbot.utility.build_context import build_context

logger = get_logger(__name__)


class LLMNode(BaseNode):
    def __init__(
        self,
        *,
        pipelines: PipelineRegistry,
        prompts: dict[str, PromptSpec],
        name: str,
        pipeline_key: str,
        prompt_key: str,
        output_key: str = "answer",
        include_history: bool = True,
        history_window: int = 5,
    ) -> None:
        self.pipelines = pipelines
        self.prompts = prompts
        self.name = name
        self.pipeline_key = pipeline_key
        self.prompt_key = prompt_key
        self.output_key = output_key
        self.include_history = include_history
        self.history_window = history_window

    @classmethod
    def from_spec(
        cls,
        spec: LLMNodeSpec,
        pipelines: PipelineRegistry,
        prompts: dict[str, PromptSpec],
    ) -> "LLMNode":
        if spec.prompt_key not in prompts:
            raise KeyError(f"Unknown prompt key: {spec.prompt_key}")

        return cls(
            pipelines=pipelines,
            prompts=prompts,
            name=spec.name,
            pipeline_key=spec.pipeline_key,
            prompt_key=spec.prompt_key,
            output_key=spec.output_key,
            include_history=spec.include_history,
            history_window=spec.history_window,
        )

    def to_spec(self) -> LLMNodeSpec:
        return LLMNodeSpec(
            kind="llm",
            name=self.name,
            pipeline_key=self.pipeline_key,
            prompt_key=self.prompt_key,
            output_key=self.output_key,
            include_history=self.include_history,
            history_window=self.history_window,
        )

    def __call__(self, state: RagState) -> dict[str, Any]:
        llm = self.pipelines.build(self.pipeline_key)
        prompt = self.prompts.get(self.prompt_key)
        if prompt is None:
            raise KeyError(f"Unknown prompt key: {self.prompt_key}")

        context = build_context(state.docs)

        prompt_vars = {
            "question": state.question,
            "context": context,
            "answer": state.answer,
        }
        rendered_prompt = prompt.template.format(**prompt_vars)

        history = state.messages[-self.history_window:] if self.include_history else []

        current_human = HumanMessage(content=rendered_prompt)

        llm_messages = []
        llm_messages.extend(history)
        llm_messages.append(current_human)

        logger.debug("Invoking LLM with %d messages", len(llm_messages))

        resp = llm.invoke(llm_messages)

        return {
            "context": context,
            self.output_key: getattr(resp, "content", ""),
            "messages": [current_human, resp],
        }
