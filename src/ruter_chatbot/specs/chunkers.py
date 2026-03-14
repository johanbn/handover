'''
Chunker specifications for consistency.
'''

from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec

default_chunker = SmartChunkerSpec()
from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec


CHUNKERS={
    "smart_chunker": SmartChunkerSpec(
                max_chunk_size=1000,
                max_overlap=30,
                semantic_min=120,
                tolerance=0.2,
            ),
}
