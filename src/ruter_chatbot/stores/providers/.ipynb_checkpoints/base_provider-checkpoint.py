from __future__ import annotations

import hashlib
import importlib
import json
import pkgutil
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Mapping, Optional, Sequence, Type

from langchain_core.documents import Document

from ruter_chatbot.types.iac.provider_spec import ProviderSpec
from ruter_chatbot.types.source import Source


class BaseProvider(ABC):
    REGISTRY: Dict[str, Type["BaseProvider"]] = {}
    _PLUGINS_LOADED: bool = False
    PLUGIN_PACKAGE = "ruter_chatbot.stores.providers"

    def __init__(self, **spec: Any):
        self.spec = spec

    @classmethod
    def register(cls, key: str):
        def deco(subcls: Type["BaseProvider"]):
            cls.REGISTRY[key] = subcls
            return subcls

        return deco

    @classmethod
    def _ensure_plugins_loaded(cls) -> None:
        if cls._PLUGINS_LOADED:
            return

        pkg_name = cls.PLUGIN_PACKAGE
        pkg = importlib.import_module(pkg_name)

        for modinfo in pkgutil.iter_modules(pkg.__path__, prefix=pkg_name + "."):
            mod_name = modinfo.name
            leaf = mod_name.rsplit(".", 1)[-1]
            if leaf in {"base_provider", "__init__"}:
                continue
            importlib.import_module(mod_name)

        cls._PLUGINS_LOADED = True

    @classmethod
    def from_spec(
        cls,
        spec: Mapping[str, Any]
        | ProviderSpec
        | Sequence[Mapping[str, Any] | ProviderSpec],
    ) -> BaseProvider:
        if isinstance(spec, Sequence) and not isinstance(
            spec, (str, bytes, bytearray, Mapping)
        ):
            return cls.from_spec(
                {
                    "type": "composite",
                    "args": {
                        "providers": list(spec),
                    },
                }
            )

        spec_obj = (
            spec if isinstance(spec, ProviderSpec) else ProviderSpec.model_validate(spec)
        )
        key = spec_obj.type

        if key not in cls.REGISTRY:
            cls._ensure_plugins_loaded()

        try:
            subcls = cls.REGISTRY[key]
        except KeyError as e:
            raise KeyError(
                f"Unknown provider type '{key}'. Registered: {list(cls.REGISTRY)}"
            ) from e

        return subcls(**spec_obj.args)

    @property
    def provider_type(self) -> str:
        return self.__class__.__name__

    @property
    def provider_id(self) -> str:
        spec_json = json.dumps(self.spec, sort_keys=True, default=str)
        spec_hash = hashlib.sha1(spec_json.encode("utf-8")).hexdigest()[:12]
        return f"{self.provider_type}:{spec_hash}"

    def list_sources(self) -> list[Source]:
        self._pre_list_sources()
        sources = list(self._iter_sources())
        return self._post_list_sources(sources)

    def _pre_list_sources(self) -> None:
        pass

    def _post_list_sources(self, sources: Sequence[Source]) -> list[Source]:
        stamped_sources: list[Source] = []

        for source in sources:
            meta = dict(source.meta)
            meta["provider_type"] = self.provider_type
            meta["provider_id"] = self.provider_id

            stamped_sources.append(
                Source(
                    type=source.type,
                    location=source.location,
                    meta=meta,
                )
            )

        return stamped_sources

    @abstractmethod
    def _iter_sources(self) -> Iterator[Source]:
        ...

    def get_docs_from_source(self, source: Source) -> list[Document]:
        self._pre_get_docs_from_source(source)
        docs = list(self._iter_docs_from_source(source))
        return self._post_get_docs_from_source(source, docs)

    def _pre_get_docs_from_source(self, source: Source) -> None:
        pass

    def _post_get_docs_from_source(
        self,
        source: Source,
        docs: Sequence[Document],
    ) -> list[Document]:
        stamped_docs: list[Document] = []

        for doc in docs:
            metadata = dict(doc.metadata)
            metadata["provider_type"] = self.provider_type
            metadata["provider_id"] = self.provider_id

            stamped_docs.append(
                Document(
                    page_content=doc.page_content,
                    metadata=metadata,
                )
            )

        return stamped_docs

    @abstractmethod
    def _iter_docs_from_source(self, source: Source) -> Iterator[Document]:
        ...
