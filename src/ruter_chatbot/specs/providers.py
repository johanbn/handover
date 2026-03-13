'''
Provides:
    ProviderSpecs that are ready for use.
'''
from ruter_chatbot.types.iac.provider_spec import ProviderSpec

ruterwiki_ks_intern = ProviderSpec(
    type="confluence",
    args={
        "base_url": "https://ruteras.atlassian.net",
        "space_keys": ["KS"],
        "include_labels": True
    }
)
ruterwiki_ks_extern = ProviderSpec(
    type="confluence",
    args={
        "base_url": "https://ruteras.atlassian.net",
        "space_keys": ["KS"],
        "include_labels": True,
        "required_label": "cb-ekstern"
    }
)
