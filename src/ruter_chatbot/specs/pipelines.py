'''
Provides various PipelineSpecs.
Conceptually a Pipeline is a model with configurations,
defined at the level where it does not reserve additional resources.
It accomplishes this by referencing a model that already reserves resources based on a ModelSpec.
Name and function derived from HuggingFacePipeline from langchain-huggingface.
'''
from ruter_chatbot.types.iac.pipeline_spec import PipelineSpec

qwen_small = PipelineSpec(
    key="qwen_small",
    type="ollama_pipeline",
    model_key="qwen_small",
    args={
        "temperature": 0.1,
    },
)
'''
Uses small Qwen model with temperature 0.1
'''

qwen_medium = PipelineSpec(
    key="qwen_medium",
    type="ollama_pipeline",
    model_key="qwen_medium",
    args={
        "temperature": 0.2,
    },
)
'''
Uses medium Qwen model with temperature 0.2
'''

llama_fast = PipelineSpec(
    key="llama_fast",
    type="ollama_pipeline",
    model_key="llama_fast",
    args={
        "temperature": 0.5,
    },
)
'''
Uses small Llama model with temperature 0.5
'''

mistral_precise = PipelineSpec(
    key="mistral_precise",
    type="ollama_pipeline",
    model_key="mistral_precise",
    args={
        "temperature": 0.0,
    },
)
'''
Uses medium-sized Mistral model with temperature 0.0
'''

claude_precise = PipelineSpec(
    key="claude_bedrock_rag",
    type="chat",
    model_key="claude_bedrock",
    args={
        "temperature": 0.0,
    },
)
'''
Uses Claude in the cloud with temperature 0.0
'''

PIPELINES={
    #"qwen_small": qwen_small,
    #"qwen_medium": qwen_medium,
    #"llama_fast": llama_fast,
    #"mistral_precise": mistral_precise,
    "claude_bedrock_rag": claude_precise,
}
'''Registry of Pipelines that are in active use.'''
