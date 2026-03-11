from pydantic import BaseModel


from ruter_chatbot.types.iac.provider_spec import ProviderSpec
from ruter_chatbot.types.iac.embed_spec import EmbedSpec
from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec

class VectorStoreSpec(BaseModel):
    name: str
    provider: ProviderSpec
    embedder: EmbedSpec
    chunker: SmartChunkerSpec
