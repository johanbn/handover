import os
import re

from langchain_community.document_loaders import ConfluenceLoader
from langchain_community.document_loaders.confluence import ContentFormat
from langchain_text_splitters import RecursiveCharacterTextSplitter

# =========================
# CONFIG
# =========================
BASE_URL = "https://ruteras.atlassian.net/wiki"
ATLASSIAN_EMAIL = "johan.norlinder@ruter.no"
ATLASSIAN_API_TOKEN = os.environ["ATLASSIAN_API_TOKEN"]  # set in PowerShell

# Pull only real pages (not folders)
CQL = 'space="KS" AND type=page'

# =========================
# LOAD
# =========================
loader = ConfluenceLoader(
    url=BASE_URL,
    username=ATLASSIAN_EMAIL,
    api_key=ATLASSIAN_API_TOKEN,
    cql=CQL,
    # export_view often yields better rendered HTML -> better text extraction
    content_format=ContentFormat.EXPORT_VIEW,
    include_labels=True,
    include_attachments=False,
    include_comments=False,
    include_archived_content=False,
    include_restricted_content=False,
    limit=500,
    max_pages=2000,
)
docs = loader.load()
print(f"Loaded {len(docs)} pages")

if False:
    # =========================
    # FILTERS / NORMALIZATION
    # =========================

    # 1) Drop embed wrapper sources (often content-poor)
    docs = [d for d in docs if "/embed/" not in (d.metadata.get("source") or "")]
    print(f"After dropping /embed/ sources: {len(docs)} pages")

    # 2) If the real /pages/... URL appears in content, use it as the source
    PAGE_URL_RE = re.compile(
        r"https://ruteras\.atlassian\.net/wiki/spaces/[^/]+/pages/\d+/[^\s]+"
    )
    for d in docs:
        m = PAGE_URL_RE.search(d.page_content or "")
        if m:
            d.metadata["source"] = m.group(0)

    # 3) Drop directory/landing pages (quick heuristic)
    def is_directory_page(doc) -> bool:
        t = (doc.page_content or "").lower()
        return any(s in t for s in [
            "siste oppdaterte artikler",
            "velkommen til ruterwiki",
            "søk i",
        ])

    docs = [d for d in docs if not is_directory_page(d)]
    print(f"After filtering directory pages: {len(docs)} pages")

    # =========================
    # CLEAN TEXT
    # =========================
    CLEAN_REPLACERS = [
        (r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", " "),   # hex colors like #C0B6F2
        (r":[a-zA-Z0-9_+-]+:", " "),                       # :mag_right:
        (r"\b[0-9a-fA-F]{4,6}\b", " "),                    # 1f50e-like tokens
        (r"\bpage\s+\d+\b", " "),                          # page 10
        (r"\bconcise\b|\btrue\b|\bfalse\b", " "),          # concise true false
        (r"[•·]+", " "),
    ]

    def clean_text(text: str) -> str:
        t = text or ""
        t = t.replace("\r\n", "\n").replace("\r", "\n")
        for pat, rep in CLEAN_REPLACERS:
            t = re.sub(pat, rep, t)
        # normalize whitespace/newlines
        t = re.sub(r"[ \t]+\n", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        t = re.sub(r"\s{2,}", " ", t)
        return t.strip()

    for d in docs:
        d.page_content = clean_text(d.page_content)

    # Drop ultra-short docs (usually macro shells / nav)
    MIN_CHARS = 200
    docs = [d for d in docs if len(d.page_content) >= MIN_CHARS]
    print(f"After short-content filter (<{MIN_CHARS} chars removed): {len(docs)} pages")
 
if True:

    MIN_CHARS = 200
    short_docs = [d for d in docs if len(d.page_content) <= MIN_CHARS and len(d.page_content) > 0]
    for d in short_docs:
        print(f"Short doc: {d.metadata.get('title')} ({len(d.page_content)} chars)")
    

    # =========================
    # CHUNKING FOR RAG
    # =========================
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(docs)

    short_chunks = [d for d in chunks if len(d.page_content) <= MIN_CHARS and len(d.page_content) > 0]
    for d in short_chunks:
        print(f"Short chunks: {d.metadata.get('title')} ({len(d.page_content)} chars)")
    
    print(len(short_docs), len(short_chunks))

    # Add trace-friendly metadata
    for c in chunks:
        c.metadata["source_url"] = c.metadata.get("source")
        c.metadata["page_title"] = c.metadata.get("title")
        c.metadata["updated_at"] = c.metadata.get("when")

    print(f"Produced {len(chunks)} chunks")

    # =========================
    # INSPECT OUTPUT
    # =========================

    print(f"Total chunks: {len(chunks)}")

    def sanitize_metadata(docs):
        cleaned = []
        for d in docs:
            md = dict(d.metadata or {})

            # Remove empty lists (Chroma rejects them)
            for k, v in list(md.items()):
                if isinstance(v, list) and len(v) == 0:
                    md.pop(k)

            # Optional: also remove None values (safe)
            for k, v in list(md.items()):
                if v is None:
                    md.pop(k)

            d.metadata = md
            cleaned.append(d)
        return cleaned

    chunks = sanitize_metadata(chunks)