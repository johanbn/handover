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
        },
    ),
}