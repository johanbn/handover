from ruter_chatbot.types.iac.graph_spec import GraphSpec, GraphCompileArgs
from ruter_chatbot.types.iac.node_spec import (
    LLMNodeSpec,
    RetrieverNodeSpec,
)
from ruter_chatbot.types.iac.edge_spec import (
    SimpleEdgeSpec,
    RouterEdgeSpec,
)


GRAPHS = {
    "demo": GraphSpec(
        state_key="structured_rag",
        compile_args=GraphCompileArgs(use_memory=False),
        nodes=[
            RetrieverNodeSpec(
                name="retrieve_docs",
                kind="retriever",
                store_key="ruter_store_aws",  # ruter_store
                top_k=5,
                output_key="docs",
            ),
            LLMNodeSpec(
                name="generate_answer",
                kind="llm",
                pipeline_key="qwen_medium",
                prompt_key="naive",
                include_history=False,
                output_key="answer",
            ),
            # LLMNodeSpec(
            #     name="generate_fast_answer",
            #     kind="llm",
            #     pipeline_key="llama_fast",
            #     prompt_key="naive",
            #     include_history=False,
            #     output_key="answer",
            # ),
            # LLMNodeSpec(
            #     name="generate_strict_answer",
            #     kind="llm",
            #     pipeline_key="mistral_precise",
            #     prompt_key="route_aware_rag_norwegian",
            #     include_history=False,
            #     output_key="answer",
            # ),
        ],
        edges=[
            SimpleEdgeSpec(
                source="retrieve_docs",
                target="generate_answer",
            ),

            # --- Showcase edges (disabled examples) ---
            # SimpleEdgeSpec(
            #     source="retrieve_docs",
            #     target="generate_fast_answer",
            # ),
            # SimpleEdgeSpec(
            #     source="retrieve_docs",
            #     target="generate_strict_answer",
            # ),
            # RouterEdgeSpec(
            #     source="retrieve_docs",
            #     state_route_field="route",
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
        compile_args=GraphCompileArgs(use_memory=True),
        nodes=[
            LLMNodeSpec(
                name="intent_classifier",
                kind="llm",
                pipeline_key="claude_bedrock_rag",
                prompt_key="intent_prompt",
                output_key="route",
            ),
            RetrieverNodeSpec(
                name="retrieve_docs",
                kind="retriever",
                store_key="ruter_store_aws",
                search_type="mmr",
                top_k=15,
                fetch_k=40,
                lambda_mult=0.5,
                output_key="docs",
            ),
            LLMNodeSpec(
                name="generate_answer",
                kind="llm",
                pipeline_key="claude_bedrock_rag",
                prompt_key="rag_prompt",
                output_key="answer",
            ),
        ],
        edges=[
            RouterEdgeSpec(
                source="intent_classifier",
                state_route_field="route",
                routes={
                    "search": "retrieve_docs",
                    "chat": "generate_answer",
                },
                default_target="generate_answer",
            ),
            SimpleEdgeSpec(
                source="retrieve_docs",
                target="generate_answer",
            ),

            # --- Showcase edges (disabled examples) ---
            # RouterEdgeSpec(
            #     source="intent_classifier",
            #     state_route_field="route",
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
        compile_args=GraphCompileArgs(use_memory=False),
        nodes=[
            RetrieverNodeSpec(
                name="retrieve_docs_aws",
                kind="retriever",
                store_key="ruter_store_aws",  # ruter_store
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
                source="retrieve_docs_aws",
                target="generate_answer_aws",
            ),
        ],
    ),
}