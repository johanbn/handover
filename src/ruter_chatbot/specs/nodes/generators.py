'''
Provides various LLMLLMNodeSpecs (Generators).
Note that node names must be unique within a GraphSpec.
However, they can be reused between GraphSpecs.
'''
from ruter_chatbot.types.iac.node_spec import NodeSpec, LLMNodeSpec

#  Answerers
llm_qwen_medium_answer: NodeSpec = LLMNodeSpec(
    name="generate_answer",
    kind="llm",
    pipeline_key="qwen_medium",
    prompt_key="naive",
    output_key="answer",
)
'''Uses medium-sized Qwen model to generate an answer.'''

llm_llama_fast_answer: NodeSpec = LLMNodeSpec(
    name="generate_fast_answer",
    kind="llm",
    pipeline_key="llama_fast",
    prompt_key="naive",
    output_key="answer",
)
'''Uses small Llama model to generate an answer.'''

llm_mistral_big_answer: NodeSpec = LLMNodeSpec(
    name="generate_strict_answer",
    kind="llm",
    pipeline_key="mistral_precise",
    prompt_key="past_answer_aware_rag_norwegian",
    output_key="answer",
)
'''Uses medium-sized Mistral model to generate answer with complex prompt.'''

llm_claude_rag_answer: NodeSpec = LLMNodeSpec(
    name="generate_answer",
    kind="llm",
    pipeline_key="claude_bedrock_rag",
    prompt_key="brief_rag_norwegian",
    output_key="answer",
)
'''
Uses Claude in the cloud with a simple RAG prompt.
'''

llm_claude_rag_no_history_answer: NodeSpec = LLMNodeSpec(
    name="generate_answer",
    kind="llm",
    pipeline_key="claude_bedrock_rag",
    prompt_key="brief_rag_norwegian",
    output_key="answer",
)
'''Uses Claude in the cloud with a simple RAG prompt without history.'''

# Classifiers
llm_claude_route_choice: NodeSpec = LLMNodeSpec(
    name="intent_classifier",
    kind="llm",
    pipeline_key="claude_bedrock_rag",
    prompt_key="search_or_chat_route_norwegian",
    output_key="route"
)
'''
Uses Claude in the cloud to determine if a question can be answered right away.
'''

llm_claude_ruter_tool_chat: NodeSpec = LLMNodeSpec(
    name="ruter_tool_chat",
    kind="llm",
    pipeline_key="claude_bedrock_rag",
    prompt_key="ruter_tool_chat_norwegian",
    tool_keys=["search_ruter_stops", "get_ruter_departures", "plan_ruter_journey", "lookup_ruter_line", "request_docs"],
    output_key="answer",
)
'''
Uses Claude in the cloud with Ruter-specific tool access.
'''
