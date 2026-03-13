
from ruter_chatbot.types.iac.embed_spec import EmbedSpec


EMBEDDER={
        "nomic-embed-text": EmbedSpec(
                type="ollama",
                args={"model": "nomic-embed-text"},
            )
}