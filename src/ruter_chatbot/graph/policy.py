from typing import Any

from pydantic import BaseModel, Field, computed_field
from langgraph.checkpoint.memory import MemorySaver

class GraphPolicy(BaseModel):
    """Policies that control Graph behavior (message visibility + runtime/compilation).

    Message policies affect what ends up in the conversation history.
    Compilation policies affect how the StateGraph is compiled (checkpointer, etc.).
    """

    # ── Message / state-management policies ──
    persist_prompt_scaffolding: bool = Field(
        default=False,
        description=(
            "Output policy. "
            "Decides if anything other than AIMessages and ToolMessages generated "
            "by Nodes will persist to messages output.\n"
            "High priority policy -> Other output policies do nothing while this is False."
        )
    )
    persist_system_messages: bool = Field(
        default=False,
        description=(
            "Output policy. "
            "Decides if SystemMessage objects will be visible in messages output.\n"
            "Low-priority policy -> loses when conflicting with any other policy."
        ),
    )
    persist_context_messages: bool = Field(
        default=True,
        description=(
            "Output policy. "
            "Decides if `context`-marked messages from PromptSpecs "
            "will be included in messages output. Takes priority over "
            "`persist_system_messages` when it implicates a `context` message."
        ),
    )
    history_window: int = Field(
        default=5,
        description=(
            "How many turns to remember.\n"
            "• negative integer → remember everything\n"
            "• 0 → remember nothing (and no checkpointer)\n"
            "• positive integer n → remember last n turns (invocations of Orchestrator.ask)"
        )
    )

    # ── Compilation directives
    @computed_field
    @property
    def use_memory(self) -> bool:
        """Whether the graph should be compiled with a checkpointer.

        Derived from `history_window` so the two can never get out of sync.
        """
        return self.history_window != 0
    
    # Future compilation knobs go here.
    # Examples:
    # interrupt_before: list[str] | None = Field(default=None, description="Nodes to interrupt before")
    # debug: bool = Field(default=False, description="Enable LangGraph debug mode")

    def get_compile_kwargs(self) -> dict[str, Any]:
        """
        Return only the kwargs that should be passed to `StateGraph.compile()`.

        Returns compile_kwargs ready for use.
        """
        kwargs: dict[str, Any] = {}
        if self.use_memory:
            kwargs["checkpointer"] = MemorySaver()
        
        return kwargs
