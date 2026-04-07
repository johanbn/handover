from ruter_chatbot.types.iac.embed_spec import EmbedSpec

ollama_nomic = EmbedSpec(
    type="ollama",
    args={
        "model": "nomic-embed-text",
    },
)
'''Straigtforward ollama-based nomic-embed-text.'''

bedrock_cohere_multilingual = EmbedSpec(
    type="bedrock",
    args={
        "model_id": "cohere.embed-multilingual-v3",
        "region_name": "eu-west-1",
    },
)
'''Bedrock-hosted cohere.embed-multilingual-v3 from eu-west-1'''

EMBEDDERS = {
    "nomic-embed-text": ollama_nomic,
    "cohere-bedrock-multilingual": bedrock_cohere_multilingual,
}
'''
Registry of embedders that are in active use.
'''
