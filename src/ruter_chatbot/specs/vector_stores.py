from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.specs.providers import ruterwiki_ks_extern, ruterwiki_ks_intern
from ruter_chatbot.specs.embedders import EMBEDDERS
from ruter_chatbot.specs.chunkers import default_chunker

ruter_store: VectorStoreSpec = VectorStoreSpec(
    key="ruter_store",
    provider=ruterwiki_ks_extern,
    embedder=EMBEDDERS["nomic-embed-text"],
    chunker=default_chunker,
)
'''
Locally hosted VectorStore for Ruter.
NOTE: locally hosted things do not work for production!
'''

ruter_store_aws = VectorStoreSpec(
    key="ruter_store_aws",
    provider=ruterwiki_ks_intern,
    embedder=EMBEDDERS["cohere-bedrock-multilingual"],
    chunker=default_chunker,
)
'''
AWS-hosted VectorStore for Ruter.
'''

VECTOR_STORES = {
    "ruter_store": ruter_store,
    "ruter_store_aws": ruter_store_aws,
}
'''
Registry of VectorStores in active use.
'''
