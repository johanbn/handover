from ruter_chatbot.types.iac.model_spec import ModelSpec

MODELS = {
    "qwen_small": ModelSpec(
        key="qwen_small",
        type="ollama_model",
        args={
            "model": "qwen2.5:3b",
            "temperature": 0.2,
        },
    ),
    "qwen_medium": ModelSpec(
        key="qwen_medium",
        type="ollama_model",
        args={
            "model": "qwen2.5:7b",
            "temperature": 0.2,
        },
    ),
    "llama_fast": ModelSpec(
        key="llama_fast",
        type="ollama_model",
        args={
            "model": "llama3.2:3b",
            "temperature": 0.3,
        },
    ),
    "mistral_precise": ModelSpec(
        key="mistral_precise",
        type="ollama_model",
        args={
            "model": "mistral:7b",
            "temperature": 0.1,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "num_ctx": 4096,
            "num_predict": 512,
        },
    ),
    "claude_bedrock": ModelSpec(
        key="claude_bedrock",
        type="bedrock_model",
        args={
            "model": "eu.anthropic.claude-sonnet-4-20250514-v1:0",
            "region_name": "eu-west-1",
            "temperature": 0.0,
            "max_tokens": 2000,
        },
    ),
}