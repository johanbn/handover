from ruter_chatbot.types.iac.vector_store_spec import VectorStoreSpec
from ruter_chatbot.specs.providers import (
    ruterwiki_ks_extern,
    ruterwiki_ks_intern,
)
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

ruter_store_aws_extern = VectorStoreSpec(
    key="ruter_store_aws_extern",
    provider=ruterwiki_ks_extern,
    embedder=EMBEDDERS["cohere-bedrock-multilingual"],
    chunker=default_chunker,
)
'''
AWS-hosted external VectorStore for Ruter.
'''

ruter_store_aws_intern = VectorStoreSpec(
    key="ruter_store_aws_intern",
    provider=[
        ruterwiki_ks_extern,
        ruterwiki_ks_intern,
    ],
    embedder=EMBEDDERS["cohere-bedrock-multilingual"],
    chunker=default_chunker,
)
'''
AWS-hosted internal VectorStore for Ruter built from multiple providers.
'''

VECTOR_STORES = {
    "ruter_store": ruter_store,
    "ruter_store_aws_extern": ruter_store_aws_extern,
    "ruter_store_aws_intern": ruter_store_aws_intern,
}
'''
Registry of VectorStores in active use.
'''
