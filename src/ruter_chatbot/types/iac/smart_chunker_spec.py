from pydantic import BaseModel

class SmartChunkerSpec(BaseModel):
    '''
    All parameters are optional.
    '''
    max_chunk_size: int | None = 1000
    '''The chunker will produce no chunks with more than max_chunk_size characters.'''
    max_overlap: int = 200
    '''The chunker will make overlap in chunk B based on the up to max_overlap last characters of chunk A.'''
    semantic_min: int | None = 120
    '''
    The chunker will make an effort to ensure each chunk contains at least
    semantic_min new characters after the overlap with the previous chunk.
    '''
    tolerance: float | None = 0.2
    '''
    The chunker calculates a target size for chunks based on above parameters.
    Tolerance is how much deviation from the target it accepts.
    Tolerance will never overrule max or min parameters, but serves a smoothing function.
    '''
    separators: list[str] | None = ["\n\n", "\n", ". ", " "]
    '''
    Separators will be applied in order when the chunker deems it necessary.
    '''
