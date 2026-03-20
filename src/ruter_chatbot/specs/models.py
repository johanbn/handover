'''
Provides various ModelSpecs.
Conceptually a "Model" is a text-generator defined at the level where it reserves resources.
'''
from ruter_chatbot.types.iac.model_spec import ModelSpec

qwen_small = ModelSpec(
    key="qwen_small",
    type="ollama_model",
    args={
        "model": "qwen2.5:3b",
        "temperature": 0.2,
    },
)
'''Small Ollama Qwen model at ~3b with low temperature'''

qwen_medium = ModelSpec(
    key="qwen_medium",
    type="ollama_model",
    args={
        "model": "qwen2.5:7b",
        "temperature": 0.2,
    },
)
'''Medium-sized Ollama Qwen model at ~7b with low temperature'''

llama_small = ModelSpec(
    key="llama_fast",
    type="ollama_model",
    args={
        "model": "llama3.2:3b",
        "temperature": 0.3,
    },
)
'''Small Ollama Llama model at ~3b with low temperature'''

mistral_precise = ModelSpec(
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
)
'''Medium-sized Ollama Mistral model at ~7b with low temperature and reptition penalty.'''

claude_precise = ModelSpec(
    key="claude_bedrock",
    type="bedrock_model",
    args={
        "model": "eu.anthropic.claude-sonnet-4-20250514-v1:0",
        "region_name": "eu-west-1",
        "temperature": 0.0,
        "max_tokens": 2000,
    },
)
'''Claude in the cloud with the lowest possible temperature.'''

MODELS = {
    #"qwen_small": qwen_small,
    #"qwen_medium": qwen_medium,
    #"llama_fast": llama_small,
    #"mistral_precise": mistral_precise,
    "claude_bedrock": claude_precise,
}
'''Registry of models that are in active use.'''
