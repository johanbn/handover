from pydantic import BaseModel

class SmartChunkerSpec(BaseModel):
    '''
    All parameters are optional.
    Undefined parameters yield defaults in the SmartChunker itself.
    '''
    max_chunk_size: int | None = None
    max_overlap: int | None
    semantic_min: int | None = None
    tolerance: float | None = None
    separators: list[str] | None = None
