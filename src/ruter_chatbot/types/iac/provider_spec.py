from __future__ import annotations

from pydantic import RootModel

from ruter_chatbot.types.iac.generic_spec import GenericSpec

class ProviderSpec(GenericSpec):
    pass


class CompositeProviderSpec(RootModel[list[ProviderSpec]]):
    pass


ProviderSpecLike = ProviderSpec | CompositeProviderSpec
