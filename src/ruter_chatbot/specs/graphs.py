from ruter_chatbot.types.iac.graph_spec import GraphSpec
from ruter_chatbot.types.iac.node_spec import (
    LLMNodeSpec,
    RetrieverNodeSpec,
    ConditionalNodeSpec,
)
from ruter_chatbot.types.iac.edge_spec import (
    SimpleEdgeSpec,
    RouterEdgeSpec,
)


GRAPH = {
    "demo": GraphSpec(
        state_key="structured_rag",
        nodes=[
            RetrieverNodeSpec(
                name="retrieve_docs",
                kind="retriever",
                store_key="ruter_store",
                top_k=5,
                output_key="docs",
            ),
            LLMNodeSpec(
                name="generate_answer",
                kind="llm",
                pipeline_key="qwen_medium_balanced",
                prompt_key="naive",
                include_history=False,
                output_key="answer",
            ),
            LLMNodeSpec(
                name="generate_fast_answer",
                kind="llm",
                pipeline_key="llama_fast_creative",
                prompt_key="naive",
                include_history=False,
                output_key="answer",
            ),
            LLMNodeSpec(
                name="generate_strict_answer",
                kind="llm",
                pipeline_key="mistral_strict_rag",
                prompt_key="route_aware_rag_norwegian",
                include_history=False,
                output_key="answer",
            ),
        ],
        edges=[
            SimpleEdgeSpec(
                kind="simple",
                source="retrieve_docs",
                target="generate_answer",
            ),

            # --- Showcase edges (disabled examples) ---
            # SimpleEdgeSpec(
            #     kind="simple",
            #     source="retrieve_docs",
            #     target="generate_fast_answer",
            # ),
            # SimpleEdgeSpec(
            #     kind="simple",
            #     source="retrieve_docs",
            #     target="generate_strict_answer",
            # ),
            # RouterEdgeSpec(
            #     kind="router",
            #     source="retrieve_docs",
            #     router_key="answer_quality_router",
            #     routes={
            #         "fast": "generate_fast_answer",
            #         "strict": "generate_strict_answer",
            #         "balanced": "generate_answer",
            #     },
            #     default_target="generate_answer",
            # ),
        ],
    ),
    "conditional_demo": GraphSpec(
        state_key="structured_rag",
        nodes=[
            LLMNodeSpec(
                name="intent_classifier",
                kind="llm",
                pipeline_key="qwen_precise",
                prompt_key="intent_prompt",
                output_key="route",
            ),
            ConditionalNodeSpec(
                name="route_from_state",
                kind="conditional",
                field="route",
            ),
            RetrieverNodeSpec(
                name="retrieve_docs",
                kind="retriever",
                store_key="ruter_store",
                top_k=5,
                output_key="docs",
            ),
            LLMNodeSpec(
                name="generate_answer",
                kind="llm",
                pipeline_key="qwen_precise",
                prompt_key="rag_prompt",
                output_key="answer",
            ),
        ],
        edges=[
            RouterEdgeSpec(
                kind="router",
                source="intent_classifier",
                router_key="route_from_state",
                routes={
                    "search": "retrieve_docs",
                    "chat": "generate_answer",
                },
                default_target="generate_answer",
            ),
            SimpleEdgeSpec(
                kind="simple",
                source="retrieve_docs",
                target="generate_answer",
            ),

            # --- Showcase edges (disabled examples) ---
            # RouterEdgeSpec(
            #     kind="router",
            #     source="intent_classifier",
            #     router_key="route_from_state",
            #     routes={
            #         "search": "retrieve_docs",
            #         "chat": "generate_answer",
            #         "smalltalk": "generate_answer",
            #     },
            #     default_target="generate_answer",
            # ),
        ],
    ),
    "aws_demo": GraphSpec(
        state_key="structured_rag",
        nodes=[
            RetrieverNodeSpec(
                name="retrieve_docs_aws",
                kind="retriever",
                store_key="ruter_store_aws",
                top_k=5,
                output_key="docs",
            ),
            LLMNodeSpec(
                name="generate_answer_aws",
                kind="llm",
                pipeline_key="claude_bedrock_rag",
                prompt_key="rag_prompt",
                include_history=False,
                output_key="answer",
            ),
        ],
        edges=[
            SimpleEdgeSpec(
                kind="simple",
                source="retrieve_docs_aws",
                target="generate_answer_aws",
            ),
        ],
    ),
}