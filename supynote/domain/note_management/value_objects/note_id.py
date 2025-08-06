"""Note ID value object."""

from uuid import UUID, uuid4
from typing import Union

from ...shared.base_value_object import SingleValueObject


class NoteId(SingleValueObject):
    """Unique identifier for a Note entity."""
    
    def __init__(self, value: Union[str, UUID]):
        if isinstance(value, str):
            value = UUID(value)
        super().__init__(value)
    
    @classmethod
    def generate(cls) -> 'NoteId':
        """Generate a new unique NoteId."""
        return cls(uuid4())
    
    @classmethod
    def from_path(cls, path: str) -> 'NoteId':
        """Create a deterministic NoteId from a file path."""
        # Use namespace UUID for file paths
        namespace = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        return cls(UUID(bytes=namespace.bytes[:8] + path.encode('utf-8')[:8]))
    
    def _validate(self, value: UUID) -> None:
        """Validate that the value is a valid UUID."""
        if not isinstance(value, UUID):
            raise ValueError(f"NoteId must be a UUID, got {type(value)}")
    
    @property
    def value(self) -> UUID:
        """Get the UUID value."""
        return self._value
    
    def to_string(self) -> str:
        """Convert to string representation."""
        return str(self._value)