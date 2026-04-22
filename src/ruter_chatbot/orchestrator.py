from __future__ import annotations

from typing import Any
from uuid import uuid4
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph

from ruter_chatbot.graph.graph_builder import GraphBuilder
from ruter_chatbot.graph.tools.tool_registry import ToolRegistry
from ruter_chatbot.llm.model_registry import ModelRegistry
from ruter_chatbot.llm.pipeline_registry import PipelineRegistry
from ruter_chatbot.logger import get_logger
from ruter_chatbot.specs.state import state_registry
from ruter_chatbot.stores.vector_store_registry import VectorStoreRegistry
from ruter_chatbot.types.app.ask import AskResponse
from ruter_chatbot.types.app.vector_store import (
    MmrSearchRequest,
    SimilaritySearchRequest,
    VectorStoreListResponse,
    VectorStoreSearchHit,
    VectorStoreSearchResponse,
)
from ruter_chatbot.types.iac.app_spec import OrchestratorSpec
from ruter_chatbot.types.iac.graph_spec import GraphSpec
from ruter_chatbot.types.iac.model_spec import ModelSpec
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec, RetrieverNodeSpec, ToolNodeSpec
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec
from ruter_chatbot.types.iac.prompt_spec import PromptSpec
from ruter_chatbot.types.iac.tool_spec import ToolSpec
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.types.spec_based import SpecBased
from ruter_chatbot.utility.get_answer_from_state import get_answer_from_state

logger = get_logger(__name__)

class Orchestrator(SpecBased[OrchestratorSpec]):
    '''
    Main class orchestrating application component interplay.
    Aims to support experimentation and production equally,
    while relying on the same code for both for consistency.

    All components revolve around a GraphSpec - a Graph Specification.
    This is used to make a LangGraph StateGraph.
    The StateGraph will draw on the other Orchestrator components for its contents.

    Orchestrator can initialize empty, and can report its own specs on demand.
    However, the Graph must be built before it can be used.
    
    Use patterns:
    
    - In development:
        * Initialize with any or all available components of each type specificied by specs.
        * Experiment with different graphs and configurations. They can be changed in place.
        * Save good settings for production with .simplify() (to make them lean), followed by .to_spec().
    
    - In production:
        * Initialize with a lean spec.
        * Expose as you see fit.
    '''
    spec_class = OrchestratorSpec

    def __init__(
        self,
        *,
        models: dict[str, ModelSpec] | None = None,
        pipelines: dict[str, PipelineSpec] | None = None,
        prompts: dict[str, PromptSpec] | None = None,
        tools: dict[str, ToolSpec] | None = None,
        vector_stores: dict[str, VectorStoreSpec] | None = None,
        graph_spec: GraphSpec | None,
    ) -> None:
        self.models: ModelRegistry = ModelRegistry.from_spec(models)
        self.pipelines: PipelineRegistry = PipelineRegistry.from_spec(pipelines, models=self.models)
        self.vector_stores: VectorStoreRegistry = VectorStoreRegistry.from_spec(vector_stores)
        self.prompts: dict[str, PromptSpec] = prompts or {}
        self.tools: ToolRegistry = ToolRegistry.from_spec(tools, vector_stores=self.vector_stores)
        self.graph_spec: GraphSpec | None = graph_spec

        self._graph: StateGraph | None = None

    @classmethod
    def from_spec(cls, spec: OrchestratorSpec | dict[str, Any]) -> "Orchestrator":
        spec_obj = spec if isinstance(spec, OrchestratorSpec) else OrchestratorSpec.model_validate(spec)

        models = spec_obj.models
        pipelines = spec_obj.pipelines
        prompts = spec_obj.prompts
        tools = spec_obj.tools
        vector_stores = spec_obj.vector_stores

        graph_spec = spec_obj.graph

        return cls(
            models=models,
            pipelines=pipelines,
            prompts=prompts,
            tools=tools,
            vector_stores=vector_stores,
            graph_spec=graph_spec,
        )

    def to_spec(self) -> OrchestratorSpec:
        return OrchestratorSpec(
            models=self.models.to_spec(),
            pipelines=self.pipelines.to_spec(),
            prompts={key: spec.model_copy(deep=True) for key, spec in self.prompts.items()},
            tools=self.tools.to_spec(),
            vector_stores=self.vector_stores.to_spec(),
            graph=self.graph_spec,
        )

    def build_graph(self, graph_spec: GraphSpec | dict[str, Any] | None = None) -> StateGraph:
        '''Builds stored GraphSpec or provided GraphSpec if feasible. Raises if not.'''
        graph_spec = graph_spec or self.graph_spec
        if graph_spec is None:
            raise ValueError("No GraphSpec provided and none stored.")

        if not isinstance(graph_spec, GraphSpec):
            graph_spec = GraphSpec.model_validate(graph_spec)
        
        for name, registry in (
            ("vector_stores", self.vector_stores),
            ("models", self.models),
            ("pipelines", self.pipelines),
            ("prompts", self.prompts)
        ):
            if not registry:
                raise ValueError(
                    f"Cannot build graph: no entries in {name}"
                )
        
        graph_builder = GraphBuilder(
            pipelines=self.pipelines,
            vector_stores=self.vector_stores,
            prompts=self.prompts,
            tools=self.tools,
        )
        graph = graph_builder.build(graph_spec)

        self.graph_spec = graph_spec
        self._graph = graph
        return self._graph

    @property
    def graph(self) -> StateGraph | None:
        '''Returns the graph if possible.'''
        if self._graph is None:
            return self.build_graph()
        return self._graph
    
    def simplify(self) -> Orchestrator:
        '''
        Reads GraphSpec to determine its dependencies.
        Removes everything else.
        Mutates in place to avoid duplicating models or embeddings.
        Returns the mutated self to enable chaining (for example, .simplify().to_spec()).
        Raises if no graph_spec was set.
        '''
        if self.graph_spec is None:
            raise ValueError(
                "Called simplify while no graph_spec was set. "
                "This would empty the Orchestrator completely and is therefore blocked."
            )
        
        used_models: set[str] = set()
        used_pipelines: set[str] = set()
        used_prompts: set[str] = set()
        used_tools: set[str] = set()
        used_vector_stores: set[str] = set()
        
        for node in self.graph_spec.nodes:
            if isinstance(node, LLMNodeSpec):
                used_pipelines.add(node.pipeline_key)
                used_prompts.add(node.prompt_key)
                used_tools.update(node.tool_keys)
            elif isinstance(node, ToolNodeSpec):
                used_tools.update(node.tool_keys)
            elif isinstance(node, RetrieverNodeSpec):
                used_vector_stores.add(node.store_key)
        
        for pipeline_key in used_pipelines:
            if pipeline_key not in self.pipelines:
                raise KeyError(f"Unknown pipeline: {pipeline_key}")
            used_models.add(
                self.pipelines.get(pipeline_key).to_spec().model_key
            )

        missing_tools = [k for k in used_tools if k not in self.tools]
        if missing_tools:
            raise KeyError(f"Unknown tool(s): {', '.join(sorted(missing_tools))}")

        for tool_key in used_tools:
            tool_spec = self.tools.get(tool_key).to_spec()
            store_key = tool_spec.args.get("store_key")
            if isinstance(store_key, str) and store_key:
                used_vector_stores.add(store_key)

        missing_prompts = [k for k in used_prompts if k not in self.prompts]
        if missing_prompts:
            raise KeyError(f"Unknown prompt(s): {', '.join(sorted(missing_prompts))}")
        
        missing_vector_stores = [
            k for k in used_vector_stores if k not in self.vector_stores
        ]
        if missing_vector_stores:
            raise KeyError(
                f"Unknown vector store(s): {', '.join(sorted(missing_vector_stores))}"
            )
        
        missing_models = [k for k in used_models if k not in self.models]
        if missing_models:
            raise KeyError(f"Unknown model(s): {', '.join(sorted(missing_models))}")
        
        self.models.keep_only(used_models)
        self.pipelines.keep_only(used_pipelines)
        self.vector_stores.keep_only(used_vector_stores)
        self.tools.keep_only(used_tools)
        self.prompts = {k: self.prompts[k] for k in used_prompts} # dict

        self._graph = None # forces rebuild from graph_spec

        return self

    def list_vector_stores(self) -> VectorStoreListResponse:
        return self.vector_stores.list_stores()
    
    def start_daily_vector_store_refreshes(
        self,
        start_hour: int,
        start_minute: int,
        stagger_by: dict[str, int] = { "hours": 0, "minutes": 30 }
    ) -> dict[str, str]:
        """
        Convenience method to start daily refresh loops for all vector stores.
        Delegates to the vector store registry.

        Does not expect the list of stores to change after starting.

        Args:
            start_hour (int): The hour (0-23) that the first refresh should start.
            start_minute (int): The minute (0-59) that the first refresh should start.
            stagger_by (dict[str, int]):
                How many `hours` and `minutes` should be between one refresh start and the next.
                Additional fields will be ignored. Missing fields are treated as 0.
                Both values must be non-negative integers.

                NOTE: Excessive staggering can cause unexpected behavior.
                Keep the cumulative stagger within a 24-hour cycle.
        
        Returns:
            dict[str, str]:
                Mapping of store key → scheduled time ("HH:MM") or error message if scheduling failed.
        """
        logger.debug(
            "Activating daily vector store refreshes: start=%02d:%02d, stagger=%s",
            start_hour, start_minute, stagger_by
        )
        result = self.vector_stores.start_daily_refreshes(
            start_hour=start_hour,
            start_minute=start_minute,
            stagger_by=stagger_by
        )
        
        logger.info(
            "Daily vector store refreshes scheduled:\n%s",
            "\n".join(f"  {k}: {v}" for k, v in sorted(result.items()))
        )

        return result

    def search_vector_store_similarity(
        self,
        request: SimilaritySearchRequest,
    ) -> VectorStoreSearchResponse:
        if request.store_name not in self.vector_stores:
            raise KeyError(f"Unknown vector store: {request.store_name}")

        store = self.vector_stores.get(request.store_name)
        results = store.similarity_search(
            request.query,
            k=request.k,
            with_score=request.with_score,
        )

        hits = VectorStoreSearchHit.from_doc_list(
            results
        )

        return VectorStoreSearchResponse(
            store_name=request.store_name,
            query=request.query,
            k=request.k,
            hits=hits,
        )

    def search_vector_store_mmr(
        self,
        request: MmrSearchRequest,
    ) -> VectorStoreSearchResponse:
        if request.store_name not in self.vector_stores:
            raise KeyError(f"Unknown vector store: {request.store_name}")

        store = self.vector_stores.get(request.store_name)
        results = store.max_marginal_relevance_search(
            request.query,
            k=request.k,
            fetch_k=request.fetch_k,
            lambda_mult=request.lambda_mult,
        )

        hits = VectorStoreSearchHit.from_doc_list(results)

        return VectorStoreSearchResponse(
            store_name=request.store_name,
            query=request.query,
            k=request.k,
            hits=hits,
        )

    def initialize(self, *store_keys: str) -> None:
        if not store_keys:
            store_keys = tuple(self.vector_stores.keys())

        missing = [key for key in store_keys if key not in self.vector_stores]
        if missing:
            raise KeyError(f"Unknown vector store(s): {', '.join(missing)}")

        for key in store_keys:
            self.vector_stores.initialize(key)

    def clear_vector_store_cache(self, *store_keys: str) -> None:
        if not store_keys:
            store_keys = tuple(self.vector_stores.keys())

        missing = [key for key in store_keys if key not in self.vector_stores]
        if missing:
            raise KeyError(f"Unknown vector store(s): {', '.join(missing)}")

        for key in store_keys:
            self.vector_stores.get(key).clear_cache()

    def ask(
        self,
        question: str,
        conversation_id: str | None = None,
        debug: bool = False,
    ) -> AskResponse:
        graph = self.graph
        use_memory = self.graph_spec.policy.use_memory
        resolved_conversation_id = conversation_id or str(uuid4()) if use_memory else None

        turn_id = uuid4()
        input_state = {
            "turn_id": turn_id,
            "question": question,
            "messages": [HumanMessage(
                content=question,
                additional_kwargs= {"turn_id": turn_id}
            )]
        }
        config = None

        if resolved_conversation_id:
            config = {
                "configurable": {
                    "thread_id": resolved_conversation_id,
                }
            }

        out = graph.invoke(input_state, config=config)
        state_type = state_registry[self.graph_spec.state_key]

        if issubclass(state_type, BaseModel):
            result = out if isinstance(out, state_type) else state_type.model_validate(out)
        else:
            result = out

        return AskResponse(
            answer=get_answer_from_state(result),
            conversation_id=resolved_conversation_id if use_memory else None,
            state=result if debug else None,
        )
