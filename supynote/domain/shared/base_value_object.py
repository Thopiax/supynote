"""Base value object class for Domain-Driven Design."""

from abc import ABC, abstractmethod
from typing import Any


class ValueObject(ABC):
    """Base class for value objects."""
    
    @abstractmethod
    def __eq__(self, other: object) -> bool:
        """Value objects are equal if all their attributes are equal."""
        pass
    
    @abstractmethod
    def __hash__(self) -> int:
        """Value objects must be hashable."""
        pass
    
    def __ne__(self, other: object) -> bool:
        """Not equal is the opposite of equal."""
        return not self.__eq__(other)
    
    @property
    @abstractmethod
    def value(self) -> Any:
        """Get the underlying value."""
        pass


class SingleValueObject(ValueObject):
    """Base class for value objects with a single value."""
    
    def __init__(self, value: Any):
        self._validate(value)
        self._value = value
    
    @property
    def value(self) -> Any:
        """Get the underlying value."""
        return self._value
    
    def __eq__(self, other: object) -> bool:
        """Equal if same type and same value."""
        if not isinstance(other, self.__class__):
            return False
        return self._value == other._value
    
    def __hash__(self) -> int:
        """Hash based on value."""
        return hash(self._value)
    
    def __str__(self) -> str:
        """String representation is the value."""
        return str(self._value)
    
    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"{self.__class__.__name__}({self._value!r})"
    
    @abstractmethod
    def _validate(self, value: Any) -> None:
        """Validate the value. Raise ValueError if invalid."""
        pass