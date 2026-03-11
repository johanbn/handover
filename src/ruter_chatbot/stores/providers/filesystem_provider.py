from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional

from langchain_core.documents import Document

from ruter_chatbot.stores.providers.base_provider import BaseProvider
from ruter_chatbot.types.source import Source


@BaseProvider.register("filesystem")
class FileSystemProvider(BaseProvider):
    def _iter_sources(self) -> Iterator[Source]:
        root = Path(self.spec["path"])
        pattern = self.spec.get("glob", "*")

        for p in root.glob(pattern):
            if p.is_file():
                stat = p.stat()
                yield Source(
                    type="filesystem",
                    location=str(p.resolve()),
                    meta={
                        "mtime_ns": stat.st_mtime_ns,
                        "size": stat.st_size,
                    },
                )

    def _iter_docs_from_source(self, source: Source) -> Iterator[Document]:
        path = Path(source.location)
        encoding = self.spec.get("encoding", "utf-8")
        text = path.read_text(encoding=encoding)

        blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]

        print(f"    [generator] reading {path.name}: {len(blocks)} block(s) found")

        for i, block in enumerate(blocks, start=1):
            print(f"    [generator] yielding doc {i} from {path.name}")

            yield Document(
                page_content=block,
                metadata={
                    "source_location": source.location,
                    "source_type": source.type,
                    "path": str(path),
                    "chunk_index": i,
                    "doc_id": f"{source.location}#chunk-{i}",
                },
            )
