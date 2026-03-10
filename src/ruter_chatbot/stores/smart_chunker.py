'''
Provides:
    SmartChunker:
        Document and String chunker that splits semantically within boundaries.
'''
import copy
import math
from langchain_core.documents import Document

from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec
from ruter_chatbot.logger import get_logger

logger = get_logger(__name__)
class SmartChunker:
    '''
    Document and String chunker that splits semantically within boundaries.
        
    Args (all optional):
        max_chunk_size (int): Chunker will never create chunks bigger than this.
        max_overlap (int): Chunker will include up to max_overlap content from the end of the previous chunk.
        semantic_min (int):
            Chunker targets a chunk size between max_chunk_size and this,
            It avoids making chunks with less than semantic_min original content where possible.
        tolerance (float):
            Flexibility-range from calculated targets,
            applied while building overlap and chunk bodies.
        separators (list(str)): Chunker will apply these in order when making splits.
        
    On init, inadvisable configurations trigger warnings.
    Mathematically impossible configurations raise ValueErrors.
    '''
    def __init__(
        self,
        max_chunk_size=1000,
        max_overlap=200,
        semantic_min=120,
        tolerance=0.2,
        separators=None,
    ):

        if max_chunk_size <= 0 or max_overlap < 0 or semantic_min < 0:
            raise ValueError("All size parameters must be non-negative, max_chunk_size > 0")

        if max_overlap >= max_chunk_size:
            raise ValueError(
                f"max_overlap ({max_overlap}) must be < max_chunk_size ({max_chunk_size})"
            )

        min_meaningful = max_overlap + semantic_min

        if max_chunk_size < semantic_min:
            raise ValueError(
                f"max_chunk_size ({max_chunk_size}) < semantic_min ({semantic_min}) → no valid chunk possible"
            )

        if max_chunk_size < min_meaningful:
            raise ValueError(
                f"max_chunk_size ({max_chunk_size}) < max_overlap ({max_overlap}) + semantic_min ({semantic_min}) → "
                "impossible to create two valid overlapping chunks"
            )

        # Very constrained splitting — usually only one chunk ever produced
        if max_chunk_size <= min_meaningful:
            raise ValueError(   # or make this a very prominent warning + force single-chunk mode
                f"max_chunk_size ({max_chunk_size}) == max_overlap + semantic_min → "
                "no meaningful splitting possible (only one chunk can ever be produced)"
            )

        # Quality warnings (tunable thresholds)
        headroom_ratio = (max_chunk_size - min_meaningful) / max_chunk_size

        if headroom_ratio < 0.10:
            logger.warning(
                "Very little headroom (%s): max_chunk_size only %s larger than "
                "overlap + min semantic size → expect low chunk variety and frequent max-size chunks",
                headroom_ratio * 100, headroom_ratio * 100 + 100
            )

        if max_overlap > 0.40 * max_chunk_size:
            logger.warning(
                "High overlap (%s of chunk size) → high redundancy expected. "
                "Consider reducing max_overlap unless you have very strong reasons.",
                (max_overlap / max_chunk_size) * 100
            )

        if semantic_min > 0.65 * max_chunk_size:
            logger.warning(
                "semantic_min (%s of max_chunk_size) is very high → limited splitting flexibility",
                (semantic_min / max_chunk_size) * 100
            )

        self.max_chunk_size = max_chunk_size
        self.max_overlap = max_overlap
        self.semantic_min = semantic_min
        self.tolerance = tolerance
        self.separators = separators or ["\n\n", "\n", ". ", " "]
        
    def split(
        self,
        text: str,
        *,
        recalculate_underway: bool = False
    ) -> list[str]:
        '''
        Main function. Splits a text while carefully trying to honor chunker parameters.
        When recalculate_underway is True,
        it re-estimates the target size after every chunk is made.
        This should reduce the chance of small tails in splitting.
        '''
        if not text:
            return []
        
        if len(text) < self.max_chunk_size:
            return [text]
        
        remaining = text
        bodies: list[str] = []
        prefixes: list[str] = []

        projected_count, target_size = self._plan_chunks(len(text))

        while remaining:
            if recalculate_underway and bodies:
                remaining_length = len(remaining)

                produced_chunks = len(bodies)
                remaining_chunks = max(1, projected_count - produced_chunks)

                # dynamic target based on remaining text
                new_target = math.ceil(remaining_length / remaining_chunks)

                # enforce constraints
                new_target = max(self.semantic_min + self.max_overlap, new_target)
                new_target = min(self.max_chunk_size, new_target)

                target_size = int((new_target + target_size) / 2)

            new_overlap = self._build_overlap(bodies[-1]) if bodies else ""

            new_body, consumed = self._build_chunk(
                remaining,
                prefix=new_overlap,
                target_size=target_size
            )

            if not new_body:
                break

            bodies.append(new_body)
            prefixes.append(new_overlap)
            remaining = remaining[consumed:]

        chunks = [p + b for b, p in zip(bodies, prefixes, strict=True)]
        return [c.strip() for c in chunks]
    
    def split_documents(
        self,
        documents: list[Document] | Document,
        *,
        recalculate_underway: bool = False
    ) -> list[Document]:
        '''
        Langchain-support for splitting.
        Applies split() to each LangChain Document it receives.
        Deepcopies metadata to the chunked Documents based on the same input Document.
        '''
        if isinstance(documents, Document):
            documents = [documents]

        split_docs: list[Document] = []
        for doc in documents:
            text = doc.page_content
            meta = doc.metadata
            chunks = self.split(
                text,
                recalculate_underway=recalculate_underway
            )
            
            for chunk in chunks:
                split_docs.append(
                    Document(page_content=chunk, metadata=copy.deepcopy(meta))
                )
        
        return split_docs
    
    @classmethod
    def from_spec(cls, spec: SmartChunkerSpec) -> "SmartChunker":
        max_chunk_size = spec.max_chunk_size
        max_overlap = spec.max_overlap
        semantic_min = spec.semantic_min
        tolerance = spec.tolerance
        separators = spec.separators
        return cls(
            max_chunk_size=max_chunk_size,
            max_overlap=max_overlap,
            semantic_min=semantic_min,
            tolerance=tolerance,
            separators=separators
        )

    # Internals

    def _build_chunk(self, text: str, prefix: str = "", target_size: int | None = None) -> tuple[str, int]:
        """
        Builds one chunk body from 'text', approximating target_size counting the prefix (overlap).
        Respects max_chunk_size and semantic_min.
        Returns: (chunk_body, characters_consumed_from_text)
        """
        hard_budget = self.max_chunk_size - len(prefix)
        target_body_size = max(0, target_size - len(prefix))
        min_body_size = self.semantic_min

        if hard_budget <= 0:
            return "", 0
        
        level = 0
        units = self._split_at_level(text, level)

        chunk_parts = []
        consumed = 0

        while units:

            unit = units[0]
            size = len(unit)

            remaining_budget = hard_budget - consumed

            # NEVER exceed max_chunk_size
            if size > remaining_budget:
                # try to split finer
                if level +1 >= len(self.separators):
                    break # cannot split further
            
                finer = self._split_at_level(unit, level + 1)

                tmp_level = level + 1
                tmp_unit = unit

                while len(finer) == 1 and tmp_level + 1 < len(self.separators):
                    tmp_level += 1
                    finer = self._split_at_level(tmp_unit, tmp_level)
            
                if len(finer) == 1:
                    break # truly atomic

                units = finer + units[1:]
                level = tmp_level
                continue

            # BEFORE semantic_min: always grow
            if consumed < min_body_size:
                chunk_parts.append(unit)
                consumed += size
                units.pop(0)
                continue

            # TARGET/TOLERANCE phase
            # Stop if we are close enough to the target
            projected = consumed + size

            if target_body_size > 0:
                upper_bound = target_body_size * (1 + self.tolerance)
                lower_bound = target_body_size * (1 - self.tolerance)

                if consumed >= target_body_size:
                    if projected > upper_bound:
                        break

                if consumed > lower_bound and consumed > self.semantic_min:
                    break

            # Otherwise add the unit
            chunk_parts.append(unit)
            consumed += size
            units.pop(0)
        
        chunk_body = "".join(chunk_parts)

        return chunk_body, consumed
    
    def _build_overlap(self, previous_chunk: str, _max_overlap: int | None = None) -> str:
        '''
        Creates an overlap for the next chunk by applying separators to the previous_chunk.
        Works back to front on the previous_chunk string, applying separators in order.
        Uses tolerance to decide if it is worth applying the next separator.
        Ensures overlap does not start mid-word, but may still start mid-sentence.
        '''
        if not previous_chunk:
            return ""
        
        budget = _max_overlap or self.max_overlap
        if budget <= 0 or self.max_overlap <= 0:
            return ""

        substring = previous_chunk[-self.max_overlap:]
        level = 0
        units = self._split_at_level(substring, level)
        overlap_parts = []
        consumed_chars = 0
        remaining_budget = budget

        while units:
            unit = units[-1] # walk backward

            size = len(unit)
            if size <= remaining_budget:
                overlap_parts.insert(0, unit)
                remaining_budget -= size
                consumed_chars += size
                units.pop()
                continue

            if level + 1 >= len(self.separators):
                break

            finer_units = self._split_at_level(unit, level + 1)

            potential_gain = 0
            for u in reversed(finer_units):
                new = len(u)
                if new + potential_gain > remaining_budget:
                    break
                potential_gain += new
            
            if potential_gain < consumed_chars * self.tolerance:
                break

            units = units[:-1] + finer_units
            level += 1
        
        overlap ="".join(overlap_parts)

        # Ensure overlap does not start mid-word.
        if overlap:
            # find start of overlap
            start_idx = len(previous_chunk) - len(overlap)
            if 0 < start_idx < len(previous_chunk):
                prev_char = previous_chunk[start_idx - 1]
                first_char = overlap[0]
                if first_char.isalnum() and prev_char.isalnum():
                    # trim until word boundary
                    cut = 0
                    while cut < len(overlap) and overlap[cut] not in " ":
                        cut += 1
                    overlap = overlap[cut:]

        return overlap
    
    def _split_at_level(self, text: str, level: int):
        if level >= len(self.separators):
            return [text]
        
        separator = self.separators[level]
        parts = text.split(separator)

        result = []
        for i, part in enumerate(parts):
            if i < len(parts) - 1:
                result.append(part + separator)
            else:
                result.append(part)
        
        return result

    def _plan_chunks(self, text_length: int) -> tuple[int, int]:

        """
        Compute the expected number of chunks and the target (average) chunk size.
        Returns:
            (expected_chunks, target_chunk_size)
        """
        # Usable chunk bodies (not counting overlap)
        max_body = self.max_chunk_size - self.max_overlap
        min_body = self.semantic_min

        # Average under optimistic assumption
        optimistic = math.ceil(text_length / max_body)
        optimistic_avg = text_length / optimistic

        if optimistic_avg < min_body:
            # Use a chunk count that ensures each chunk >= semantic_min
            chunk_count = max(1, text_length // min_body)
        else:
            chunk_count = optimistic
        
        target_size = math.ceil(text_length / chunk_count)

        target_size = max(self.semantic_min + self.max_overlap, target_size)
        target_size = min(self.max_chunk_size, target_size)

        projected_chunk_count = chunk_count

        return projected_chunk_count, target_size
