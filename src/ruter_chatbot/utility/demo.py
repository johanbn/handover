from __future__ import annotations

import asyncio

from ruter_chatbot.orchestrator import Orchestrator

from ruter_chatbot.types.iac.app_spec import AppSpec
from ruter_chatbot.types.iac.model_spec import ModelSpec
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec
from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.types.iac.embed_spec import EmbedSpec
from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec
from ruter_chatbot.types.iac.graph_spec import GraphSpec
from ruter_chatbot.types.iac.node_spec import LLMNodeSpec, RetrieverNodeSpec
from ruter_chatbot.types.iac.edge_spec import SimpleEdgeSpec

from ruter_chatbot.specs.prompts import PROMPTS
from ruter_chatbot.specs.providers import ruterwiki_ks


APP = AppSpec(
    models={
        "qwen_base": ModelSpec(
            key="qwen_base",
            type="ollama_model",
            args={
                "model": "qwen2.5:3b",
                "temperature": 0.2,
            },
        ),
    },

    pipelines={
        "qwen_precise": PipelineSpec(
            key="qwen_precise",
            type="ollama_pipeline",
            model_key="qwen_base",
            args={"temperature": 0.2},
        ),
    },

    prompts={
        "naive": PROMPTS["naive"],
    },

    vector_stores={
        "ruter_store": VectorStoreSpec(
            name="ruter_store",
            provider=ruterwiki_ks,
            embedder=EmbedSpec(
                type="ollama",
                args={"model": "nomic-embed-text"},
            ),
            chunker=SmartChunkerSpec(
                max_chunk_size=400,
                max_overlap=200,
                semantic_min=120,
                tolerance=0.2,
            ),
        ),
    },

    graph=GraphSpec(
        state_key="rag_state",
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
                pipeline_key="qwen_precise",
                prompt_key="naive",
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
        ],
    ),
)

async def main() -> None:
    orch = Orchestrator(APP)

    print("Initializing vector stores...")
    await orch.initialize()
    print("Ready.\n")

    while True:
        q = input("You: ").strip()

        if not q:
            continue

        if q.lower() in {"exit", "quit"}:
            break

        answer = await orch.ask(q)
        print("\nAssistant:", answer)
        print("")


if __name__ == "__main__":
    asyncio.run(main())