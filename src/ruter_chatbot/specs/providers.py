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
        "include_labels": True,
        "required_label": "cb-intern",
        "required_label_id": "597393410",
    }
)
'''
Permissive Provider for RuterWiki limited to the KS space.
'''

ruterwiki_ks_extern = ProviderSpec(
    type="confluence",
    args={
        "base_url": "https://ruteras.atlassian.net",
        "space_keys": ["KS"],
        "include_labels": True,
        "required_label": "cb-ekstern",
        "required_label_id": "596770823",
    }
)
'''
Restrictive Provider for RuterWiki limited to pages labeled 'cb-ekstern' in the KS space.
'''
