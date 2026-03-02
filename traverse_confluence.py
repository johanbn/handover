import os
import time
import json
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple
import requests

# =========================
# CONFIG
# =========================
BASE_URL = "https://ruteras.atlassian.net/wiki"
SPACE_KEY = "KS"

ATLASSIAN_EMAIL = "johan.norlinder@ruter.no"
ATLASSIAN_API_TOKEN = os.environ["ATLASSIAN_API_TOKEN"]

# Start points (set these!)
ROOT_PAGE_IDS = ["89064195"
    # "123456789",  # <-- put your root page id(s) here
]

# Optional: stop traversal if a page has any of these labels
STOP_LABELS = {"no-ingest", "do-not-index", "private"}

# Optional: skip ingest but still traverse children if label present
SKIP_INGEST_LABELS = {"skip-index"}

OUT_JSONL = "confluence_ingested.jsonl"

REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_CALLS_SEC = 0.1  # be nice to the API


# =========================
# HTTP HELPERS
# =========================
def _session() -> requests.Session:
    s = requests.Session()
    s.auth = (ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN)
    s.headers.update({"Accept": "application/json"})
    return s


def _get_json(s: requests.Session, url: str, params: Optional[dict] = None) -> dict:
    r = s.get(url, params=params, timeout=REQUEST_TIMEOUT)
    if r.status_code == 429:
        # rate limited
        retry_after = int(r.headers.get("Retry-After", "2"))
        time.sleep(retry_after)
        r = s.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    time.sleep(SLEEP_BETWEEN_CALLS_SEC)
    return r.json()


# =========================
# CONFLUENCE API
# =========================
def fetch_page(
    s: requests.Session,
    page_id: str,
) -> Dict:
    """
    Fetch a single page with rendered HTML and labels.
    """
    url = f"{BASE_URL}/rest/api/content/{page_id}"
    params = {
        "expand": ",".join(
            [
                "body.export_view",
                "version",
                "space",
                "ancestors",
                "metadata.labels",
            ]
        )
    }
    return _get_json(s, url, params=params)


def fetch_child_pages(
    s: requests.Session,
    page_id: str,
    limit: int = 200,
) -> List[Dict]:
    """
    Fetch direct child pages (with pagination).
    Returns list of child summaries with id/title/_links.
    """
    results: List[Dict] = []
    start = 0

    while True:
        url = f"{BASE_URL}/rest/api/content/{page_id}/child/page"
        params = {"limit": limit, "start": start}
        data = _get_json(s, url, params=params)

        batch = data.get("results", [])
        results.extend(batch)

        size = data.get("size", len(batch))
        if size == 0:
            break

        # Confluence uses _links.next sometimes; start/limit is reliable enough
        if len(batch) < limit:
            break
        start += limit

    return results


def cql_find_page_ids_by_title(
    s: requests.Session,
    title: str,
    space_key: str = SPACE_KEY,
    limit: int = 25,
) -> List[str]:
    """
    Convenience lookup: get page ids matching a title in a space.
    Useful for finding ROOT_PAGE_IDS once.
    """
    url = f"{BASE_URL}/rest/api/content/search"
    cql = f'space="{space_key}" AND type=page AND title ~ "{title}"'
    params = {"cql": cql, "limit": limit}
    data = _get_json(s, url, params=params)
    return [x["id"] for x in data.get("results", [])]


# =========================
# TEXT CLEANUP
# =========================
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

def html_to_text(html: str) -> str:
    # Very simple stripper. If you want better extraction later, swap this out.
    text = _TAG_RE.sub(" ", html or "")
    text = _WS_RE.sub(" ", text).strip()
    return text


def get_labels(page: Dict) -> Set[str]:
    labels = page.get("metadata", {}).get("labels", {}).get("results", []) or []
    return {l.get("name", "") for l in labels if l.get("name")}


# =========================
# GATING LOGIC (YOU CONTROL THIS)
# =========================
def should_ingest_and_traverse(page: Dict, text: str, labels: Set[str]) -> Tuple[bool, bool]:
    """
    Returns: (ingest_this_page, traverse_children)

    Customize to your needs.
    """
    # Hard stop: do not ingest and do not traverse below
    if labels & STOP_LABELS:
        return (False, False)

    # Skip ingest but keep walking down the tree
    if labels & SKIP_INGEST_LABELS:
        return (False, True)

    # Example heuristic: if it's basically empty, still traverse children
    if len(text) < 50:
        return (False, True)

    # Default: ingest and traverse
    return (True, True)


# =========================
# TRAVERSAL
# =========================
def traverse_tree_dfs(
    s: requests.Session,
    root_ids: Iterable[str],
) -> Iterable[Dict]:
    """
    DFS traversal yielding fully fetched page payloads.
    """
    visited: Set[str] = set()
    stack: List[str] = list(reversed(list(root_ids)))

    while stack:
        page_id = stack.pop()
        if page_id in visited:
            continue
        visited.add(page_id)

        page = fetch_page(s, page_id)
        yield page

        # Child traversal decision happens outside (after you inspect page)
        # so we don't push children here yet.


def ingest_tree(
    root_ids: List[str],
    out_jsonl: str = OUT_JSONL,
) -> None:
    s = _session()

    if not root_ids:
        raise ValueError(
            "ROOT_PAGE_IDS is empty. Add one or more Confluence page IDs to start from."
        )

    visited: Set[str] = set()
    stack: List[str] = list(reversed(root_ids))

    ingested_count = 0
    seen_count = 0

    with open(out_jsonl, "w", encoding="utf-8") as f:
        while stack:
            page_id = stack.pop()
            if page_id in visited:
                continue
            visited.add(page_id)

            page = fetch_page(s, page_id)
            seen_count += 1

            title = page.get("title", "")
            space = page.get("space", {}).get("key", "")
            html = page.get("body", {}).get("export_view", {}).get("value", "") or ""
            text = html_to_text(html)
            labels = get_labels(page)

            ingest, traverse = should_ingest_and_traverse(page, text, labels)

            print(
                f"[{seen_count}] {space}:{title} (id={page_id}) "
                f"labels={sorted(labels)} ingest={ingest} traverse={traverse}"
            )

            if ingest:
                record = {
                    "id": page_id,
                    "title": title,
                    "space": space,
                    "url": f"{BASE_URL}{page.get('_links', {}).get('webui', '')}",
                    "labels": sorted(labels),
                    "text": text,
                    "version": page.get("version", {}).get("number"),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                ingested_count += 1

            if traverse:
                children = fetch_child_pages(s, page_id)
                # DFS: push children onto stack
                for child in reversed(children):
                    cid = child.get("id")
                    if cid and cid not in visited:
                        stack.append(cid)

    print(f"\nDone. Seen {seen_count} pages, ingested {ingested_count} -> {out_jsonl}")


if __name__ == "__main__":
    ingest_tree(ROOT_PAGE_IDS)