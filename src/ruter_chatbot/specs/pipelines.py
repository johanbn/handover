from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec


PIPELINES={
    "qwen_small_precise": PipelineSpec(
        key="qwen_small_precise",
        type="ollama_pipeline",
        model_key="qwen_small",
        args={
            "temperature": 0.1,
        },
    ),
    "qwen_medium_balanced": PipelineSpec(
        key="qwen_medium_balanced",
        type="ollama_pipeline",
        model_key="qwen_medium",
        args={
            "temperature": 0.2,
        },
    ),
    "llama_fast_creative": PipelineSpec(
        key="llama_fast_creative",
        type="ollama_pipeline",
        model_key="llama_fast",
        args={
            "temperature": 0.5,
        },
    ),
    "mistral_strict_rag": PipelineSpec(
        key="mistral_strict_rag",
        type="ollama_pipeline",
        model_key="mistral_precise",
        args={
            "temperature": 0.0,
        },
    ),
    "claude_bedrock_rag": PipelineSpec(
        key="claude_bedrock_rag",
        type="chat",
        model_key="claude_bedrock",
        args={
            "temperature": 0.0,
        },
    ),
}
