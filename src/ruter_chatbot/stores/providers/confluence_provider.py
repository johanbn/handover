from __future__ import annotations

import os
from typing import Any, Iterator, Optional
from urllib.parse import urljoin

import requests
from langchain_community.document_loaders.confluence import (
    ConfluenceLoader, ContentFormat
)
from langchain_core.documents import Document

from ruter_chatbot.types.source import Source
from ruter_chatbot.stores.providers.base_provider import BaseProvider
from ruter_chatbot.utility.secrets import secrets

@BaseProvider.register("confluence")
class ConfluenceProvider(BaseProvider):
    """
    Provider that reads content from a Confluence Cloud instance via REST API.
    Looks for authentication details in secrets and in environment
    """

    API_VERSION = "v2"

    def __init__(
        self,
        *,
        base_url: str,                          # https://yourcompany.atlassian.net
        space_keys: Optional[list[str]] = None, # Limit to these spaces (recommended)
        include_labels: bool = False,
        include_comments: bool = False,
        include_archived_content: bool = False,
        api_version: str = API_VERSION,
        timeout: float = 30.0,
        **spec: Any
    ):
        super().__init__(**spec)

        self.base_url = base_url.rstrip("/") + "/"
        self.api_version = api_version
        self.timeout = timeout
        
        # We check both, but as a rule of thumb:
        # email in env, api_token in secrets
        self.email = secrets.get("confluence_email") or os.getenv("CONFLUENCE_EMAIL")
        self.api_token = secrets.get("confluence_token") or os.getenv("CONFLUENCE_TOKEN")

        if not self.email or not self.api_token:
            raise ValueError("Confluence credentials missing from environment and secrets (email + api_token)")
        
        self.space_keys = space_keys or []

        self.include_labels = include_labels
        self.include_comments = include_comments
        self.include_archived_content = include_archived_content

        self._session = self._build_session()

    # HTTP helpers
    
    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.auth = (self.email, self.api_token)
        session.headers["Accept"] = "application/json"
        return session
    
    def _api_url(self, path: str) -> str:
        if path.startswith("/wiki/"):
            url = urljoin(self.base_url, path.lstrip("/"))
        else:
            url = urljoin(
                self.base_url,
                f"wiki/api/{self.api_version}/" + path.lstrip("/")
            )
        return url
    
    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = self._api_url(path)
        resp = self._session.request(
            method, url, timeout=self.timeout, **kwargs
        )
        resp.raise_for_status()
        return resp.json()

    # Source listing
    
    def _iter_sources(self) -> Iterator[Source]:
        """
        Enumerate pages as Sources.
        """

        if not self.space_keys:
            raise ValueError(
                "ConfluenceProivder requires 'space_keys' to avoid scanning entire instance."
            )
        
        for space_key in self.space_keys:
            yield from self._iter_space_pages(space_key)
        
    
    def _iter_space_pages(self, space_key: str) -> Iterator[Source]:
        """
        Iterate all pages in a space.
        """

        path = "pages"
        params: dict[str, Any] = {
            "spaceKey": space_key,
            "limit": 100,
            "status": "current" if not self.include_archived_content else "any",
        }

        while True:
            data = self._request(
                "GET",
                path,
                params=params
            )

            for page in data.get("results", []):
                page_id = page["id"]
                title = page.get("title")

                webui = page.get("_links", {}).get("webui", "")
                page_url = urljoin(self.base_url, webui)

                version = page.get("version", {}).get("number") # not page version.

                yield Source(
                    type="confluence",
                    location=page_url,
                    meta={
                        "page_id": page_id,
                        "space_key": space_key,
                        "title": title,
                        "version": version
                    },
                )
            
            next_link = data.get("_links", {}).get("next")

            if not next_link:
                break

            path = next_link
            params = None
    
    # Document loading

    def _iter_docs_from_source(self, source: Source) -> Iterator[Document]:
        """
        Convert a Source (page) into Documents using LangChain loader.
        """

        page_id = source.meta.get("page_id")

        if not page_id:
            raise ValueError("Source missing page_id")
        
        loader = ConfluenceLoader(
            url=self.base_url,
            username=self.email,
            api_key=self.api_token,
            content_format=ContentFormat.VIEW,
            page_ids=[page_id],
            include_comments=self.include_comments,
            include_labels=self.include_labels,
            include_attachments=False, # disabled for now out of dislike for how it does this.
        )

        docs = loader.load()

        for doc in docs:
            metadata = dict(doc.metadata)
            metadata.update(
                {
                    "confluence_page_id": page_id,
                    "confluence_space": source.meta.get("space_key"),
                    "confluence_url": source.location,
                    "confluence_title": source.meta.get("title"),
                    "confluence_version": source.meta.get("version"),
                }
            )

            yield Document(
                page_content=doc.page_content,
                metadata=metadata,
            )

if __name__ == "__main__":
    spec = {
        "type": "confluence",
        "args": {
            "base_url": "https://ruteras.atlassian.net",
            "space_keys": ["KS"]
        }
    }
    prov = BaseProvider.from_spec(spec)
    pages = prov.list_sources()
    print(f"Got {len(pages)} Sources.")
    sample_docs = prov.get_docs_from_source(pages[0])
    print(sample_docs)
