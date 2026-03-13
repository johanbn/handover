from ruter_chatbot.types.iac.graph_spec import GraphSpec
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec, RetrieverNodeSpec
from ruter_chatbot.types.iac.edge_spec import SimpleEdgeSpec

GRAPH = {
    "demo": GraphSpec(
        state_key="rag_state",
        nodes=[
            RetrieverNodeSpec(
                name="retrieve_docs",
                kind="retriever",
                store_key="ruter_store",
                top_k=5,
                output_key="docs",
            ),

            # Default answer node
            LLMNodeSpec(
                name="generate_answer",
                kind="llm",
                pipeline_key="qwen_medium_balanced",
                prompt_key="naive",
                include_history=False,
                output_key="answer",
            ),

            # Optional alternative answer nodes
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
            # Swap target to another node if you want a different default
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
        ],
    ),
}