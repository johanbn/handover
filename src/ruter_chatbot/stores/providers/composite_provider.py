from __future__ import annotations

from typing import Any, Iterator, Sequence

from langchain_core.documents import Document

from ruter_chatbot.stores.providers.base_provider import BaseProvider
from ruter_chatbot.types.iac.provider_spec import CompositeProviderSpec, ProviderSpec
from ruter_chatbot.types.source import Source


@BaseProvider.register("composite")
class CompositeProvider(BaseProvider):
    """
    Stateless provider that composes multiple providers.

    Standard operations are delegated to the provider that owns a source.
    CompositeProvider itself should remain invisible in source/document metadata.
    """

    def __init__(self, **spec: Any):
        super().__init__(**spec)

        provider_specs = self.spec.get("providers", [])
        if not isinstance(provider_specs, list):
            raise TypeError("'providers' must be a list")

        self.providers: list[BaseProvider] = [
            BaseProvider.from_spec(p) for p in provider_specs
        ]

        self._providers_by_id: dict[str, BaseProvider] = {
            p.provider_id: p for p in self.providers
        }
    
    def to_spec(self) -> CompositeProviderSpec:
        specs: list[ProviderSpec] = []
        for provider in self.providers:
            provider_spec = provider.to_spec()
            if not isinstance(provider_spec, ProviderSpec):
                raise TypeError(
                    "CompositeProvider only supports child providers that serialize "
                    "to ProviderSpec."
                )
            specs.append(provider_spec)
        return CompositeProviderSpec(root=specs)

    def _iter_sources(self) -> Iterator[Source]:
        """
        Attach provider identity to sources so later operations can be
        routed back to the correct provider.
        """
        for provider in self.providers:
            for source in provider.list_sources():
                yield source

    def _post_list_sources(self, sources: Sequence[Source]) -> list[Source]:
        """
        Do not restamp **sources** in the composite.

        Child providers already stamp source metadata, and the composite
        should remain transparent.
        """
        return list(sources)

    def _iter_docs_from_source(self, source: Source) -> Iterator[Document]:
        """
        Forward document loading to the provider that owns the source.
        """
        provider = self._provider_for_source(source)
        yield from provider.get_docs_from_source(source)

    def _post_get_docs_from_source(
        self,
        source: Source,
        docs: Sequence[Document],
    ) -> list[Document]:
        """
        Do not restamp **documents** in the composite.

        Child providers already stamp document metadata, and the composite
        should remain transparent.
        """
        return list(docs)

    def _provider_for_source(self, source: Source) -> BaseProvider:
        """Resolve which provider owns a given source."""
        provider_id = source.meta.get("provider_id")
        if not isinstance(provider_id, str):
            raise KeyError(
                f"Source at '{source.location}' is missing 'provider_id' in meta"
            )

        try:
            return self._providers_by_id[provider_id]
        except KeyError as e:
            raise KeyError(
                f"No child provider found for provider_id='{provider_id}'. "
                f"Known providers: {list(self._providers_by_id)}"
            ) from e
