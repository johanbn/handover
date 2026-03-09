from __future__ import annotations

import json
from pathlib import Path

from ruter_chatbot.stores.providers.base_provider import BaseProvider


"""
Base abstractions for content providers.

A provider is responsible for:
1. listing available sources from some backend,
2. converting a source into one or more langchain Documents.

Providers are registered by type string via @BaseProvider.register(...),
and instantiated dynamically through BaseProvider.from_spec(...).

Typical usage:
    provider = BaseProvider.from_spec(spec)
    sources = provider.list_sources()

    for source in sources:
        docs = provider.get_docs_from_source(source)
        ...
"""


def main() -> None:
    data_dir = (Path(__file__).resolve().parent / "data").resolve()

    try_spec = 1

    if try_spec == 1:
        # Explicit composite spec
        spec = {
            "type": "composite",
            "args": {
                "providers": [
                    {
                        "type": "filesystem",
                        "args": {
                            "path": data_dir,
                            "glob": "*.txt",
                        },
                    },
                    {
                        "type": "filesystem",
                        "args": {
                            "path": data_dir,
                            "glob": "*.md",
                        },
                    },
                ]
            },
        }

    elif try_spec == 2:
        # Implicit composite (list of provider specs)
        spec = [
            {
                "type": "filesystem",
                "args": {
                    "path": data_dir,
                    "glob": "*.txt",
                },
            },
            {
                "type": "filesystem",
                "args": {
                    "path": data_dir,
                    "glob": "*.md",
                },
            },
        ]

    elif try_spec == 3:
        # Single provider
        spec = {
            "type": "filesystem",
            "args": {
                "path": data_dir,
                "glob": "*.txt",
            },
        }

    provider = BaseProvider.from_spec(spec)

    print("Provider type:", provider.provider_type)
    print("Provider id:", provider.provider_id)
    print("Provider class:", type(provider))
    print("Provider spec:")
    print(json.dumps(provider.spec, indent=2, ensure_ascii=False, default=str))

    sources = provider.list_sources()
    print(f"\nFound {len(sources)} source(s)\n")

    for source in sources:
        print("PROCESSING SOURCE:", source.location)

        docs = provider.get_docs_from_source(source)
        print(f"  get_docs_from_source returned: {type(docs)} (len={len(docs)})")

        for doc in docs:
            print("DOC METADATA:")
            print(json.dumps(doc.metadata, indent=2, ensure_ascii=False, default=str))
            print("CONTENT:")
            print(doc.page_content)
            print("-" * 60)


if __name__ == "__main__":
    main()