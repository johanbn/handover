import copy
import math
from langchain_core.documents import Document

class SmartChunker:
    def __init__(
        self,
        max_chunk_size=1000,
        overlap=200,
        semantic_min=120,
        tolerance=0.2,
        separators=None,
        _depth=0,
        _max_depth=3, # runaway recursion-protection
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.semantic_min = semantic_min
        self.tolerance = tolerance
        self._depth = _depth
        self._max_depth = _max_depth
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
        n = len(text)
        if n <= self.max_chunk_size:
            return [text]
        
        stride = self.max_chunk_size - self.overlap
        chunks_needed = math.ceil((n - self.overlap) / stride)
        chunk_size = min(self.max_chunk_size, math.ceil(n / chunks_needed))
        min_chunk = self.overlap + self.semantic_min
        tolerance = int(chunk_size * self.tolerance)
        chunks = []
        start = 0
        
        while start < n:
            target_end = min(start + chunk_size, n)
            
            # tail case
            if target_end == n:
                tail = text[start:n]
                
                if not chunks:
                    chunks.append(tail)
                    break
                
                if len(tail) >= min_chunk:
                    chunks.append(tail)
                    break
                
                # stump handling (len(tail) < min_chunk)
                prev = chunks[-1]
                
                merged = self._safe_concat(prev, tail)
                if len(merged) <= self.max_chunk_size:
                    chunks[-1] = merged
                    break
                
                # try local recursion
                if self._depth < self._max_depth:
                    merged = self._safe_concat(prev, tail)
                    sub = SmartChunker(
                        max_chunk_size=self.max_chunk_size,
                        overlap=self.overlap,
                        semantic_min=self.semantic_min,
                        tolerance=self.tolerance,
                        separators=self.separators,
                        _depth=self._depth + 1,
                        _max_depth=self._max_depth,
                    ).split(merged)
                    
                    if len(sub) >= 2:
                        chunks[-1] = sub[0]
                        chunks.extend(sub[1:])
                    
                    else: # fallback: accept stump
                        chunks.append(tail)

                else:
                    chunks.append(tail)
                    break
                
            split_point = self._find_split(
                text,
                start,
                target_end,
                chunk_size,
                min_chunk
            )

            if split_point <= start:
                split_point = target_end
                
            chunk = text[start:split_point].rstrip()
                
            if len(chunk) < min_chunk and chunks:
                candidate = self._safe_concat(chunks[-1], chunk)
                    
                if len(candidate) <= self.max_chunk_size:
                    chunks[-1] = candidate
                
                else:
                    chunks.append(chunk)
    
            else:
                chunks.append(chunk)
            
            start = max(0, split_point - self.overlap)
                
        return chunks
    
    def _find_split(
            self,
            text: str,
            start: int,
            target_end: int,
            chunk_size: int,
            min_chunk: int
        ) -> int:
        search_start = start + min_chunk
        
        search_region = text[search_start:target_end]
        for i, sep in enumerate(self.separators):
            idx = search_region.rfind(sep)
            if idx == -1:
                continue
            
            pos = search_start + idx + len(sep)
            # one-step lookahead
            if i + 1 < len(self.separators):
                next_sep = self.separators[i + 1]
                next_idx = search_region.rfind(next_sep)
                
                if next_idx != -1:
                    next_pos = search_start + next_idx + len(next_sep)
                    
                    if next_pos >= pos + int(chunk_size * self.tolerance):
                        return next_pos
                
            return pos
        
        return target_end
    
    def _safe_concat(
        self,
        prev: str,
        nxt: str
    ) -> str:
        if not prev:
            return nxt
        
        if not nxt:
            return prev
        
        needs_space = (prev and not prev[-1].isspace()) and (nxt and not nxt[0].isspace())
        
        return (prev + (" " if needs_space else "") + nxt)
    
    def split_documents(
        self,
        documents: list[Document]
    ) -> list[Document]:
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
