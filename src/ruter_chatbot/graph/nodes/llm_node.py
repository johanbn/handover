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
PROMPT_WRAPPER_KEY = "ruter_chatbot_prompt_wrapper"


class LLMNode(BaseNode):
    def __init__(
        self,
        *,
        pipelines: PipelineRegistry,
        prompts: dict[str, PromptSpec],
        name: str,
        pipeline_key: str,
        prompt_key: str,
        tool_keys: list[str] | None = None,
        tools: list[Any] | None = None,
        output_key: str = "answer",
        include_history: bool = True,
        history_window: int = 5,
    ) -> None:
        self.pipelines = pipelines
        self.prompts = prompts
        self.name = name
        self.pipeline_key = pipeline_key
        self.prompt_key = prompt_key
        self.tool_keys = tool_keys or []
        self.tools = tools or []
        self.output_key = output_key
        self.include_history = include_history
        self.history_window = history_window

    @classmethod
    def from_spec(
        cls,
        spec: LLMNodeSpec,
        pipelines: PipelineRegistry,
        prompts: dict[str, PromptSpec],
        tools_registry: Any | None = None,
    ) -> "LLMNode":
        if spec.prompt_key not in prompts:
            raise KeyError(f"Unknown prompt key: {spec.prompt_key}")

        tools = []
        if spec.tool_keys:
            if tools_registry is None:
                raise ValueError("LLM node declares tools, but no tool registry was provided.")
            tools = tools_registry.get_many(spec.tool_keys)

        return cls(
            pipelines=pipelines,
            prompts=prompts,
            name=spec.name,
            pipeline_key=spec.pipeline_key,
            prompt_key=spec.prompt_key,
            tool_keys=list(spec.tool_keys),
            tools=tools,
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
            tool_keys=list(self.tool_keys),
            output_key=self.output_key,
            include_history=self.include_history,
            history_window=self.history_window,
        )

    def __call__(self, state: RagState) -> dict[str, Any]:
        llm = self.pipelines.build(self.pipeline_key)
        if self.tools:
            llm = llm.bind_tools(self.tools)
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

        full_history = state.messages if self.include_history else []
        history_tail_type = (
            getattr(full_history[-1], "type", None) if full_history else None
        )

        if history_tail_type == "tool":
            # During a tool loop we must preserve the prompt wrapper that initiated
            # the tool call so the model can continue the same exchange coherently.
            filtered_history = list(full_history)
        else:
            filtered_history = [
                msg
                for msg in full_history
                if not getattr(msg, "additional_kwargs", {}).get(PROMPT_WRAPPER_KEY)
            ]

        history = (
            filtered_history[-self.history_window:]
            if self.include_history
            else []
        )
        if history and getattr(history[0], "type", None) == "tool":
            # Bedrock tool conversations must keep the preceding tool-use message
            # together with the tool result; a blind history window can split them.
            history = list(filtered_history)

        llm_messages = list(history)
        history_tail_type = getattr(history[-1], "type", None) if history else None
        should_append_prompt = history_tail_type != "tool"
        current_human = HumanMessage(
            content=rendered_prompt,
            additional_kwargs={PROMPT_WRAPPER_KEY: True},
        )
        if should_append_prompt:
            llm_messages.append(current_human)

        logger.debug("Invoking LLM with %d messages", len(llm_messages))

        resp = llm.invoke(llm_messages)
        content = getattr(resp, "content", "")
        answer_text = "" if content is None else str(content)
        emitted_messages = [resp]
        if should_append_prompt:
            emitted_messages.insert(0, current_human)

        return {
            "context": context,
            self.output_key: answer_text,
            "messages": emitted_messages,
        }
