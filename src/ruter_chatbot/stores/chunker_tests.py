from ruter_chatbot.logger import get_logger
from ruter_chatbot.stores.smart_chunker import SmartChunker

logger = get_logger(__name__)

text_1 = """
Urban community gardens have gradually become hubs of renewal in many neighborhoods, offering shared spaces where residents cultivate vegetables, flowers, and friendships. Their quiet rows of soil provide a sense of purpose, and the simple act of tending to plants often helps people rediscover a calmer rhythm amid the noise of daily routines.

As these gardens expand, volunteers frequently introduce small projects that strengthen the sense of cooperation. Some build wooden benches or create shaded corners for reading, while others focus on maintaining compost systems. Over time, these contributions transform the area into a living tapestry of practical skill, creativity, and shared responsibility that grows alongside the plants themselves.

Researchers have begun studying the broader effects of community gardening on local well‑being, noting patterns that go beyond the produce harvested each season. Participants often report feeling more connected to their neighbors, and many describe increased motivation to care for nearby parks and walkways. These subtle shifts accumulate, gradually shaping a more resilient social environment that benefits everyone involved.

Yet despite all this progress, a single neglected corner or abandoned tool shed can undermine the sense of harmony, reminding everyone how easily an otherwise thriving space can feel disjointed when one small element falls out of place.
"""

text_2 = """This is a document that contains one extremely long sentence without any line breaks or periods near the desired split points so the splitter has to fall back to spaces or even characters because the quick brown fox jumps over the lazy dog many times while we continue adding clause after clause in a steadily flowing stream that intentionally refuses to pause or end in any tidy location since the whole purpose of this construction is to force the algorithm to rely on the coarsest separator possible when trying to segment the text for processing and as we keep writing and writing and stretching the structure further it becomes clear that any attempt to locate natural boundaries will fail because we have deliberately removed them in order to test how the search region logic behaves under extreme conditions where chunk sizes expand far beyond typical thresholds and the tolerance-based lookahead is compelled to decide whether to prefer larger chunks or accidentally slip into producing tiny incremental steps simply because there are no punctuation anchors available anywhere in this endlessly extending linguistic chain."""

text_3 = """
# Introduction

Short intro.

## Very Long Section

This section is deliberately long and has many sentences without double newlines in between. We want to see whether the splitter prefers to cut at \n (single newline) rather than . when it can get substantially more content by doing so. Sentence one. Sentence two. Sentence three. Sentence four. Sentence five. Sentence six. Sentence seven that is quite a bit longer than the others because we are testing the lookahead logic very carefully now.

## Short Section

Only a few words here.
"""

text_4 = """
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
Psych. End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
Psycho end of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
End of chunk candidate. End of chunk candidate. End of chunk candidate. End of chunk candidate.
"""
'''Very sorry about this test existing.'''

text_1_chunker = SmartChunker(max_chunk_size=700, max_overlap=150, semantic_min=180, tolerance=0.25)
text_2_chunker = SmartChunker(max_chunk_size=450, max_overlap=120, semantic_min=300, tolerance=0.15)
text_3_chunker = SmartChunker(max_chunk_size=600, max_overlap=140, semantic_min=160, tolerance=0.3, separators=["\n\n", "\n", ". ", " "])
text_4_chunker = SmartChunker(max_chunk_size=800, max_overlap=250, semantic_min=140, tolerance=0.18)

chunkers = [
    text_1_chunker,
    text_2_chunker, # This one is designed to be unreasonable -> expected to fail -> but how badly?
    text_3_chunker,
    text_4_chunker
]
texts = [text_1, text_2, text_3, text_4]

for i, chunker in enumerate(chunkers):
    logger.info("With Chunker: %d", i + 1)
    
    for id, text in enumerate(texts):
        logger.info("On text: %d", id + 1)
        
        entries = []
        had_problem = False
        split_text = chunker.split(text, recalculate_underway=True)
        if len(split_text) == 0:
            logger.warning("Text produced no chunks!")
        for idx, chunk in enumerate(split_text):
            min_chunk_size = (chunker.semantic_min + chunker.max_overlap) * 0.9
            if idx == 0:
                min_chunk_size = chunker.semantic_min
                
            too_small = min_chunk_size > len(chunk)
            if too_small:
                had_problem = True
                
            entries.append((min_chunk_size, idx, too_small, chunk))
        
        if had_problem:
            for min_size, idx, too_small, chunk in entries:
                logger.info(idx)
                logger.info("Minimum chunk size target: %d", int(min_size))
                logger.info("Chunk size: %d", len(chunk))
                logger.info("Too small? %s", too_small)
                logger.info(chunk)
                logger.info("")   # empty line between chunks
        else:
            logger.info("Text yielded %d chunks.", len(split_text))
