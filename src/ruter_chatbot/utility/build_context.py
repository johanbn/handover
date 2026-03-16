
from langchain_core.documents import Document


def build_context(docs: list[Document], max_chars_per_doc: int = 10_000) -> str:
    if not docs:
        return ""

    parts: list[str] = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        text = doc.page_content.strip()[:max_chars_per_doc]
        parts.append(f"[Doc {i} | source={source}]\n{text}")

    return "\n\n".join(parts)
