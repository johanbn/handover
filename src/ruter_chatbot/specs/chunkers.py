'''
Chunker specifications for consistency.
'''

from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec

default_chunker = SmartChunkerSpec()
'''SmartChunker with all parameters set to their defaults.'''

reduced_chunker = SmartChunkerSpec(
    max_chunk_size=800,
    max_overlap=50,
    semantic_min=50,
    tolerance=0.2,
)
'''SmartChunker with reduced max_chunk_size, max_overlap and semantic_min.'''
