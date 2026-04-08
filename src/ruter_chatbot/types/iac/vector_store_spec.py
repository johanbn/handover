from pydantic import BaseModel
from typing import Sequence

from ruter_chatbot.types.iac.provider_spec import ProviderSpecLike
from ruter_chatbot.types.iac.embed_spec import EmbedSpec
from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec

class VectorStoreSpec(BaseModel):
    key: str
    provider: ProviderSpecLike
    embedder: EmbedSpec
    chunker: SmartChunkerSpec
