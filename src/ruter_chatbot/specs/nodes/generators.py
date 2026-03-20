'''
Provides various LLMNodeSpecs (Generators).
Note that node names must be unique within a GraphSpec.
However, they can be reused between GraphSpecs.
'''
from ruter_chatbot.types.iac.node_spec import NodeSpec

#  Answerers
llm_qwen_medium_answer: NodeSpec = NodeSpec(
    name="generate_answer",
    kind="llm",
    pipeline_key="qwen_medium",
    prompt_key="naive",
    include_history=False,
    output_key="answer",
)
'''Uses medium-sized Qwen model to generate an answer.'''

llm_llama_fast_answer: NodeSpec = NodeSpec(
    name="generate_fast_answer",
    kind="llm",
    pipeline_key="llama_fast",
    prompt_key="naive",
    include_history=False,
    output_key="answer",
)
'''Uses small Llama model to generate an answer.'''

llm_mistral_big_answer: NodeSpec = NodeSpec(
    name="generate_strict_answer",
    kind="llm",
    pipeline_key="mistral_precise",
    prompt_key="past_answer_aware_rag_norwegian",
    include_history=False,
    output_key="answer",
)
'''Uses medium-sized Mistral model to generate answer with complex prompt.'''

llm_claude_rag_answer: NodeSpec = NodeSpec(
    name="generate_answer",
    kind="llm",
    pipeline_key="claude_bedrock_rag",
    prompt_key="brief_rag_norwegian",
    output_key="answer",
)
'''
Uses Claude in the cloud with a simple RAG prompt.
'''

llm_claude_rag_no_history_answer: NodeSpec = NodeSpec(
    name="generate_answer",
    kind="llm",
    pipeline_key="claude_bedrock_rag",
    prompt_key="brief_rag_norwegian",
    include_history=False,
    output_key="answer",
)
'''Uses Claude in the cloud with a simple RAG prompt without history.'''

# Classifiers
llm_claude_route_choice: NodeSpec = NodeSpec(
    name="intent_classifier",
    kind="llm",
    pipeline_key="claude_bedrock_rag",
    prompt_key="search_or_chat_route_norwegian",
    output_key="route"
)
'''
Uses Claude in the cloud to determine if a question can be answered right away.
'''