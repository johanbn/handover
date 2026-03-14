from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.specs.providers import ruterwiki_ks
from ruter_chatbot.specs.embedder import EMBEDDER
from ruter_chatbot.specs.chunker import CHUNKER

VECTOR_STORES = {
    "ruter_store": VectorStoreSpec(
        name="ruter_store",
        provider=ruterwiki_ks,
        embedder=EMBEDDER["nomic-embed-text"],
        chunker=CHUNKER["smart_chunker"],
    ),
    "ruter_store_aws": VectorStoreSpec(
        name="ruter_store_aws",
        provider=ruterwiki_ks,
        embedder=EMBEDDER["cohere-bedrock-multilingual"],
        chunker=CHUNKER["smart_chunker"],
    ),
}