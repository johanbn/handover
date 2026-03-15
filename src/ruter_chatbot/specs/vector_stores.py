from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.specs.providers import ruterwiki_ks
from ruter_chatbot.specs.embedders import EMBEDDERS
from ruter_chatbot.specs.chunkers import CHUNKERS

VECTOR_STORES = {
    "ruter_store": VectorStoreSpec(
        name="ruter_store",
        provider=ruterwiki_ks,
        embedder=EMBEDDERS["nomic-embed-text"],
        chunker=CHUNKERS["smart_chunker"],
    ),
    "ruter_store_aws": VectorStoreSpec(
        name="ruter_store_aws",
        provider=ruterwiki_ks,
        embedder=EMBEDDERS["cohere-bedrock-multilingual"],
        chunker=CHUNKERS["smart_chunker"],
    ),
}