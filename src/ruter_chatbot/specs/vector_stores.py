from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.specs.providers import ruterwiki_ks_extern, ruterwiki_ks_intern
from ruter_chatbot.specs.embedders import EMBEDDERS
from ruter_chatbot.specs.chunkers import default_chunker

VECTOR_STORES = {
    "ruter_store": VectorStoreSpec(
        name="ruter_store",
        provider=ruterwiki_ks_extern,
        embedder=EMBEDDERS["nomic-embed-text"],
        chunker=default_chunker,
    ),
    "ruter_store_aws": VectorStoreSpec(
        name="ruter_store_aws",
        provider=ruterwiki_ks_intern,
        embedder=EMBEDDERS["cohere-bedrock-multilingual"],
        chunker=default_chunker,
    ),
}