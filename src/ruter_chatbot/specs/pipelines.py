from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec


PIPELINES={
    "qwen_small": PipelineSpec(
        key="qwen_small",
        type="ollama_pipeline",
        model_key="qwen_small",
        args={
            "temperature": 0.1,
        },
    ),
    "qwen_medium": PipelineSpec(
        key="qwen_medium",
        type="ollama_pipeline",
        model_key="qwen_medium",
        args={
            "temperature": 0.2,
        },
    ),
    "llama_fast": PipelineSpec(
        key="llama_fast",
        type="ollama_pipeline",
        model_key="llama_fast",
        args={
            "temperature": 0.5,
        },
    ),
    "mistral_precise": PipelineSpec(
        key="mistral_precise",
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
