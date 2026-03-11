'''
Provides:
    ProviderSpecs that are ready for use.
'''
from ruter_chatbot.types.iac.provider_spec import ProviderSpec

ruterwiki_ks = ProviderSpec(
    type="confluence",
    args={
        "base_url": "https://ruteras.atlassian.net",
        "space_keys": ["KS"]
    }
)