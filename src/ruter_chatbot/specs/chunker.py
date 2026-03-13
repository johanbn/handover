from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec


CHUNKER={
    "smart_chunker": SmartChunkerSpec(
                max_chunk_size=1000,
                max_overlap=30,
                semantic_min=120,
                tolerance=0.2,
            ),
}