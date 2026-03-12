from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from ruter_chatbot.graph.nodes.base import BaseNode
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.state_spec import RagState


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

        # -----------------------------
        # QUICK RAG HACK
        # Build context from retrieved docs
        # -----------------------------
        docs = getattr(state, "docs", [])

        if docs:
            context = "\n\n".join(
                f"[Doc {i+1}]\n{d.page_content}"
                for i, d in enumerate(docs)
            )
        else:
            context = ""

        # Update state context
        state.context = context

        # -----------------------------
        # Render prompt
        # -----------------------------
        rendered_prompt = self.prompt_template.format(**state.model_dump())

        # -----------------------------
        # Build message list
        # -----------------------------
        messages = []

        if self.include_history:
            messages.extend(state.messages[-self.history_window:])

        messages.append(HumanMessage(content=rendered_prompt))

        # -----------------------------
        # Call LLM
        # -----------------------------
        resp = llm.invoke(messages)

        return {
            self.output_key: getattr(resp, "content", ""),
            "messages": state.messages + [resp],
        }