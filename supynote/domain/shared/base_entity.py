"""Base entity class for Domain-Driven Design."""

from abc import ABC
from typing import Any, List
from datetime import datetime


class DomainEvent:
    """Base class for domain events."""
    
    def __init__(self):
        self.occurred_at = datetime.now()


class Entity(ABC):
    """Base class for domain entities."""
    
    def __init__(self, entity_id: Any):
        self._id = entity_id
        self._domain_events: List[DomainEvent] = []
    
    @property
    def id(self) -> Any:
        """Get the entity's unique identifier."""
        return self._id
    
    def __eq__(self, other: object) -> bool:
        """Entities are equal if they have the same ID."""
        if not isinstance(other, Entity):
            return False
        return self._id == other._id
    
    def __hash__(self) -> int:
        """Hash based on entity ID."""
        return hash(self._id)
    
    def _raise_event(self, event: DomainEvent) -> None:
        """Raise a domain event."""
        self._domain_events.append(event)
    
    def collect_events(self) -> List[DomainEvent]:
        """Collect and clear domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events


class AggregateRoot(Entity):
    """Base class for aggregate roots."""
    
    def __init__(self, entity_id: Any):
        super().__init__(entity_id)
        self._version = 0
    
    @property
    def version(self) -> int:
        """Get the aggregate version for optimistic locking."""
        return self._version
    
    def increment_version(self) -> None:
        """Increment the version after successful persistence."""
        self._version += 1