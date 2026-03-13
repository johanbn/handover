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
from ruter_chatbot.logger import get_logger

logger = get_logger(__name__)

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
        base_url: str,                              # https://yourcompany.atlassian.net
        space_keys: Optional[list[str]] = None,     # Limit to these spaces (recommended)
        required_label: Optional[str] = None,       # Limit to this tag
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
        self.required_label = required_label or ""

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
        '''Generic API request method for ConfluenceProvider.'''
        url = self._api_url(path)
        resp = self._session.request(
            method, url, timeout=self.timeout, **kwargs
        )
        resp.raise_for_status()
        return resp.json()
    
    def _paginated_request(self, method: str, path: str, **kwargs) -> dict:
        '''
        Extension of ConfluenceProvider._request.
        Calls _request(), then again with the "_next" url until none exist.
        Trusting that resp.json() contains a list of "results",
        ConfluenceProvider._paginated_request() extends them in a list.
        Returns original response with extended results.
        '''
        # first time outside loop
        data = self._request(method=method, path=path, **kwargs)
        results = data.get("results", [])
        next_link = data.get("_links", {}).get("next")
        while next_link:
            # trust next link to reflect kwargs
            follow_up_data = self._request(method=method, path=next_link)
            results.extend(follow_up_data.get("results", []))
            next_link = follow_up_data.get("_links", {}).get("next")
        data["results"] = results
        return data

    def _resolve_label_id(self) -> str:
        if not self.required_label:
            self._label_id = ""
            return self._label_id
        
        if hasattr(self, "_label_id"):
            return self._label_id
        
        data = self._paginated_request(
            "GET",
            "labels",
        )

        results = data.get("results", [])

        self._label_id = next(
            (label["id"] for label in results if label.get("name") == self.required_label),
            ""
        )
        if not self._label_id:
            raise ValueError(f"Couldn't find id of required label {self.required_label}")
        return self._label_id

    # Source listing
    
    def _iter_sources(self) -> Iterator[Source]:
        """
        Enumerate pages as Sources.
        """

        if not self.space_keys:
            logger.warning(
                "ConfluenceProvider is best used with 'space_keys' to avoid scanning entire instance."
            )
            # request list of spaces
            data = self._paginated_request("GET", "spaces")
        
        else:
            data = self._paginated_request(
                "GET",
                "spaces",
                params={ "keys": self.space_keys }
            )

        results = data.get("results", [])
        space_ids: list[str] = [result["id"] for result in results]
        
        if self.required_label:
            yield from self._iter_labeled_pages(space_ids)
        
        else:
            for space_id in space_ids:
                yield from self._iter_space_pages(space_id)

    def _iter_page_results(self, results: list[Any], with_label: bool = False) -> Iterator[Source]:
        '''
        Handle the core results from an iterator.
        '''
        for page in results:
            page_id = page["id"]
            space_id = page["spaceId"]
            title = page.get("title")

            webui = page.get("_links", {}).get("webui", "")
            page_url = urljoin(self.base_url, webui)

            version_metadata = page.get("version", {})
            version = version_metadata.get("number") # not page version.
            last_modified = version_metadata.get("createdAt")
            meta = {
                "page_id": page_id,
                "space_id": space_id,
                "title": title,
                "version": version,
                "last_modified": last_modified
            }
            if with_label:
                meta["label"] = self.required_label

            yield Source(
                type="confluence",
                location=page_url,
                meta=meta,
            )
    
    def _iter_labeled_pages(self, space_ids: list[str]) -> Iterator[Source]:
        """
        Iterate all pages with a label across specified spaces.
        """
        label_id = self._resolve_label_id()
        if not label_id:
            logger.warning(
                "Attempted to iterate labeled pages without resolving label_id"
            )
            return

        path = f"labels/{label_id}/pages"
        params: dict[str, Any] = {
            "space_id": space_ids,
            "limit": 100,
            "status": "current" if not self.include_archived_content else "any",
        }
        data = self._paginated_request(
            "GET",
            path,
            params=params
        )

        yield from self._iter_page_results(
            data.get(
                "results",
                []
            ),
            with_label=True
        )
    
    def _iter_space_pages(self, space_id: str) -> Iterator[Source]:
        """
        Iterate all pages in a space.
        """
        path = "pages"
        params: dict[str, Any] = {
            "space-id": [space_id],
            "limit": 100,
            "status": "current" if not self.include_archived_content else "any",
        }

        data = self._paginated_request(
            "GET",
            path,
            params=params
        )

        yield from self._iter_page_results(
            data.get(
                "results",
                []
            ),
            with_label=False
        )
    
    # Document loading

    def _iter_docs_from_source(self, source: Source) -> Iterator[Document]:
        """
        Convert a Source (page) into Documents using LangChain loader.
        """
        if self.required_label:
            source_label = source.meta.get("label")
            if self.required_label != source.meta.get("label", ""):
                logger.warning(
                    "Attempted use of ConfluenceProvider with `required_label` %s "
                    "to load from Source without that label; Loading nothing instead. "
                    "Label on source: %s",
                    self.required_label,
                    source_label
                    )
                return

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
                    "confluence_space": source.meta.get("space_id"),
                    "confluence_url": source.location,
                    "confluence_title": source.meta.get("title"),
                    "confluence_version": source.meta.get("version"),
                    "last_modified": source.meta.get("last_modified")
                }
            )

            yield Document(
                page_content=doc.page_content,
                metadata=metadata,
            )
