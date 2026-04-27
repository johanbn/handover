from typing import Protocol, runtime_checkable

@runtime_checkable
class Keyed(Protocol):
    '''Enforces the need for a key, allowing safe usage in SpecBasedRegistries.'''
    key: str
