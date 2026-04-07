'''
Provides class:
    SpecBasedRegistry:
        Shared base for registries that hold SpecBased objects.
'''
from typing import ClassVar, Generic, TypeVar, Union, Iterable, Type
from abc import ABC

from ruter_chatbot.types.spec_based import SpecBased, SpecT

RuntimeT = TypeVar("RuntimeT", bound=SpecBased[SpecT])

class SpecBasedRegistry(ABC, Generic[RuntimeT, SpecT]):
    '''
    Shared base for registries that hold SpecBased objects.
    Requires the SpecBased class to have a `key` attribute or property,
    Use Keyed when defining Runtime classes to make this explicit.
    '''
    runtime_class: ClassVar[Type[SpecBased[SpecT]]]

    def __init__(
        self,
        items: Iterable[Union[RuntimeT, SpecT]] | None = None,
    ) -> None:
        self._items: dict[str, RuntimeT] = {}
        for obj in items or []:
            self.add(obj)
    
    @classmethod
    def from_spec(cls, specs: dict[str, SpecT] | None = None, **kwargs):
        registry = cls(**kwargs)
        for spec in (specs or {}).values():
            registry.add(spec)
        return registry

    def add(self, obj: Union[RuntimeT, SpecT]) -> RuntimeT:
        runtime = self.runtime_class.ensure(obj)
        self._items[runtime.key] = runtime
        return runtime
    
    def get(self, key:str) -> RuntimeT:
        if key not in self._items:
            raise KeyError(f"Unknown key: {key}")
        return self._items[key]

    def remove(self, key:str) -> RuntimeT:
        try:
            return self._items.pop(key)
        except KeyError:
            raise KeyError(f"Cannot remove non-existent key: {key}")
    
    def keep_only(self, keys: set[str]) -> None:
        for key in list(self._items.keys()):
            if key not in keys:
                self.remove(key)
    
    def to_spec(self) -> dict[str, SpecT]:
        return {
            key: runtime.to_spec()
            for key, runtime in self._items.items()
        }
    
    def keys(self):
        return self._items.keys()
    
    def values(self):
        return self._items.values()
    
    def items(self):
        return self._items.items()
    
    def __contains__(self, key:str) -> bool:
        return key in self._items

    def __len__(self) -> int:
        return len(self._items)