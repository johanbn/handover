from __future__ import annotations

from typing import Any
from langchain_core.messages import AIMessage

from ruter_chatbot.graph.nodes.base import BaseNode
from ruter_chatbot.graph.policy import GraphPolicy
from ruter_chatbot.graph.policies.input import apply_history_window_to_messages
from ruter_chatbot.graph.policies.output import sanitize_messages_for_output
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.logger import get_logger
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.state_spec import RagState
from ruter_chatbot.utility.build_context import build_context
from ruter_chatbot.utility.with_turn_id import with_turn_id

logger = get_logger(__name__)

class LLMNode(BaseNode):
    def __init__(
        self,
        *,
        pipelines: PipelineRegistry,
        prompts: dict[str, PromptSpec],
        policy: GraphPolicy,
        name: str,
        pipeline_key: str,
        prompt_key: str,
        tool_keys: list[str] | None = None,
        tools: list[Any] | None = None,
        output_key: str = "answer",
    ) -> None:
        self.pipelines = pipelines
        self.prompts = prompts
        self.name = name
        self.pipeline_key = pipeline_key
        self.prompt_key = prompt_key
        self.tool_keys = tool_keys or []
        self.tools = tools or []
        self.output_key = output_key
        self.policy = policy

    @classmethod
    def from_spec(
        cls,
        spec: LLMNodeSpec,
        pipelines: PipelineRegistry,
        policy: GraphPolicy,
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
            policy=policy
        )

    def to_spec(self) -> LLMNodeSpec:
        return LLMNodeSpec(
            kind="llm",
            name=self.name,
            pipeline_key=self.pipeline_key,
            prompt_key=self.prompt_key,
            tool_keys=list(self.tool_keys),
            output_key=self.output_key
        )

    def __call__(self, state: RagState) -> dict[str, Any]:
        turn_id = state.turn_id
        llm = self.pipelines.build(self.pipeline_key)

        if self.tools:
            llm = llm.bind_tools(self.tools)

        prompt = self.prompts[self.prompt_key]

        context = build_context(state.docs)

        prompt_vars = {
            "question": state.question,
            "context": context,
            "answer": state.answer,
        }

        rendered_prompt = prompt.render_messages(turn_id=turn_id, **prompt_vars)

        raw_history = state.messages or []

        history = apply_history_window_to_messages(raw_history, self.policy)
        llm_messages = history + rendered_prompt
        logger.debug("Invoking LLM with %d messages", len(llm_messages))

        resp: AIMessage = with_turn_id(
            llm.invoke(llm_messages),
            turn_id=turn_id
        )

        answer_text = str(resp.text)

        emitted_messages = rendered_prompt + [resp]
        filtered_output = sanitize_messages_for_output(
            emitted_messages,
            policy=self.policy
        )

        return {
            self.output_key: answer_text,
            "messages": filtered_output,
        }
