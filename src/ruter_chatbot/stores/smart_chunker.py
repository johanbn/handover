import copy
from langchain_core.documents import Document

from ruter_chatbot.types.iac.smart_chunker_spec import SmartChunkerSpec

class SmartChunker:
    def __init__(
        self,
        max_chunk_size=1000,
        max_overlap=200,
        semantic_min=120,
        tolerance=0.2,
        separators=None,
    ):
        self.max_chunk_size = max_chunk_size
        self.max_overlap = max_overlap
        self.semantic_min = semantic_min
        self.tolerance = tolerance
        self.separators = separators or [
            "\n\n",
            "\n",
            ". ",
            " ",
        ]
        
    def split(
        self,
        text: str
    ) -> list[str]:
        if not text:
            return []
        
        remaining = text
        chunks: list[str] = []
        previous_chunk = ""

        while remaining:
            overlap_prefix = self._build_overlap(previous_chunk)
            chunk_body, consumed = self._build_chunk(
                remaining,
                prefix=overlap_prefix
            )

            chunk_text = (overlap_prefix + chunk_body)

            if not chunk_text:
                break

            chunks.append(chunk_text)

            previous_chunk = chunk_text
            remaining = remaining[consumed:]
        
        return [c.strip() for c in chunks]
    
    def split_documents(
        self,
        documents: list[Document] | Document
    ) -> list[Document]:

        if isinstance(documents, Document):
            documents = [documents]

        split_docs: list[Document] = []
        for doc in documents:
            text = doc.page_content
            meta = doc.metadata
            chunks = self.split(text)
            
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

    def _build_chunk(self, text: str, prefix: str = "") -> tuple[str, int]:
        """
        Builds one chunk body from 'text', respecting max_chunk_size
        including the prefix (overlap).
        Returns: (chunk_body, characters_consumed_from_text)
        """
        remaining_budget = self.max_chunk_size - len(prefix)
        if remaining_budget <= 0:
            return "", 0
        
        level = 0
        units = self._split_at_level(text, level)

        chunk_parts = []
        consumed_chars = 0

        while units:
            unit = units[0]
            size = len(unit)
            

            if size <= remaining_budget: # Unit fits in chunk
                chunk_parts.append(unit)
                remaining_budget -= size
                consumed_chars += size
                units.pop(0)
                continue

            # Unit doesn't fit
            if level + 1 >= len(self.separators):
                break # atomic level reached

            finer_units = self._split_at_level(unit, level + 1)

            # tolerance check
            potential_gain = 0
            for u in finer_units:
                new = len(u)
                if new + potential_gain > remaining_budget:
                    break
                potential_gain += new

            if potential_gain < consumed_chars * self.tolerance:
                break # not worth descending
            
            # replace this unit with its finer units
            units = finer_units + units[1:]
            level += 1
        
        chunk_body = "".join(chunk_parts)

        # Check against semantic_min
        if (
            len(chunk_body) < self.semantic_min
            and consumed_chars < len(text)
        ):
            # try one more descent pass if possible
            pass # minimal policy for now

        return chunk_body, consumed_chars
    
    def _build_overlap(self, previous_chunk: str) -> str:
        if not previous_chunk or self.max_overlap <= 0:
            return ""
        
        substring = previous_chunk[-self.max_overlap:]
        level = 0
        units = self._split_at_level(substring, level)
        overlap_parts = []
        consumed_chars = 0
        remaining_budget = self.max_overlap

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
