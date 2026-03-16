'''
Chunker specifications for consistency.
'''

from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec

default_chunker = SmartChunkerSpec()

CHUNKERS={
    "smart_chunker": SmartChunkerSpec(
                max_chunk_size=800,
                max_overlap=50,
                semantic_min=50,
                tolerance=0.2,
            ),
}
