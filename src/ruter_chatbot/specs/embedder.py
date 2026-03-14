from ruter_chatbot.types.iac.embed_spec import EmbedSpec

EMBEDDER = {
    "nomic-embed-text": EmbedSpec(
        type="ollama",
        args={"model": "nomic-embed-text"},
    ),
    "cohere-bedrock-multilingual": EmbedSpec(
        type="bedrock",
        args={
            "model_id": "cohere.embed-multilingual-v3",
            "region_name": "eu-west-1",
        },
    ),
}