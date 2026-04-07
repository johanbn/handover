'''
Provides classes:
    SpecBased:
        Base class for runtime components driven by a spec.

    SimpleSpecBased:
        Extension of SpecBased for classes where all attributes translate directly to specs.
'''
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Generic, ClassVar, Union

from pydantic import BaseModel

SpecT = TypeVar("SpecT", bound=BaseModel)
InstanceT = TypeVar("InstanceT", bound="SpecBased[SpecT]")

class SpecBased(ABC, Generic[SpecT]):
    """
    Base class for all runtime components that are driven by a Pydantic spec.

    Every subclass must define:
        - spec_class: the Pydantic model class that describes its configuration
        - from_spec(cls, spec: SpecT) -> Self
        - to_spec(self) -> SpecT
    
    In return they get:
        - predictable isomorphic behavior
        - ensure(cls, obj) -> cls if obj is a spec or class instance.
    """

    spec_class: ClassVar[Type[SpecT]]

    @classmethod
    @abstractmethod
    def from_spec(cls, spec: SpecT) -> "SpecBased[SpecT]":
        """Create an instance from its spec."""
        ...

    @classmethod
    def ensure(
        cls: Type[InstanceT],
        obj: Union[InstanceT, SpecT],
    ) -> InstanceT:
        """
        Ensure we have an instance of this class.

        - If `obj` is already an instance of `cls`, return it as-is.
        - If `obj` is an instance of `cls.spec_class`, create a new instance
          using `from_spec`.
        - Otherwise, raise a clear TypeError.
        """
        if isinstance(obj, cls):
            return obj

        if isinstance(obj, cls.spec_class):
            return cls.from_spec(obj)  # type: ignore[arg-type]

        raise TypeError(
            f"Expected an instance of {cls.__name__} or its spec "
            f"{cls.spec_class.__name__}, got {type(obj).__name__} instead."
        )
    
    @abstractmethod
    def to_spec(self) -> SpecT:
        """Create a spec from its instance."""
        ...

class SimpleSpecBased(SpecBased[SpecT], Generic[SpecT]):
    """
    Extension of SpecBased for classes where all
    attributes translate directly to specs.
    """

    @classmethod
    def from_spec(cls, spec) -> "SimpleSpecBased[SpecT]":
        # Default: pass all fields to __init__
        return cls(**spec.model_dump())
    
    def to_spec(self) -> SpecT:
        # build spec from public attributes on the spec
        data = {
            field: getattr(self, field)
            for field in self.spec_class.model_fields
            if hasattr(self, field)
        }
        return self.spec_class.model_validate(data)
