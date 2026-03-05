from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from ruter_chatbot.stores.providers.base_provider import BaseProvider


def main() -> None:
    data_dir = (Path(__file__).resolve().parent / "data").resolve()

    spec = {
        "type": "filesystem",
        "args": {"path": data_dir, "glob": "*.txt"},
    }

    provider = BaseProvider.from_spec(spec)

    print("Provider type:", provider.provider_type)
    print("Provider id:", provider.provider_id)
    print("Provider class:", type(provider))
    print("spec path type:", type(provider.spec["path"]), provider.spec["path"])

    state_store: Dict[str, Mapping[str, Any]] = {}

    sources = provider.list_sources()
    print(f"\nFound {len(sources)} source(s)\n")

    for source in sources:
        previous_state = state_store.get(source.location)

        if not provider.has_changed(source, since=previous_state):
            print("UNCHANGED:", source.location)
            continue

        print("PROCESSING SOURCE:", source.location)

        docs = provider.get_docs_from_source(source)
        print(f"  get_docs_from_source returned: {type(docs)} (len={len(docs)})")

        for doc in docs:
            print("DOC METADATA:")
            print(json.dumps(doc.metadata, indent=2, ensure_ascii=False, default=str))
            print("CONTENT:")
            print(doc.page_content)
            print("-" * 60)

        state_store[source.location] = source.meta

    print("\nState store:")
    print(json.dumps(state_store, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()