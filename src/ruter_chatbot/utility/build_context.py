from langchain_core.documents import Document


def build_context(
    docs: list[Document | tuple[Document, float]],
    max_chars_per_doc: int = 10_000,
) -> str:
    if not docs:
        return ""

    parts: list[str] = []

    for i, item in enumerate(docs, start=1):
        score: float | None = None

        if isinstance(item, tuple):
            doc, score = item
        else:
            doc = item

        source = doc.metadata.get("source", "unknown")
        text = doc.page_content.strip()[:max_chars_per_doc]

        header = f"[Doc {i} | source={source}"
        if score is not None:
            header += f" | score={score:.4f}"
        header += "]"

        parts.append(f"{header}\n{text}")

    return "\n\n".join(parts)