"""Note repository interface."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.note import Note
from ..value_objects.note_id import NoteId
from ..value_objects.note_path import NotePath
from ..value_objects.time_range_filter import TimeRangeFilter


class NoteRepository(ABC):
    """Repository interface for Note aggregate."""
    
    @abstractmethod
    def find_by_id(self, note_id: NoteId) -> Optional[Note]:
        """Find a note by its ID."""
        pass
    
    @abstractmethod
    def find_by_path(self, path: NotePath) -> Optional[Note]:
        """Find a note by its path."""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Note]:
        """Get all notes."""
        pass
    
    @abstractmethod
    def find_by_directory(self, directory: str) -> List[Note]:
        """Find all notes in a directory."""
        pass
    
    @abstractmethod
    def find_with_filter(self, time_filter: TimeRangeFilter) -> List[Note]:
        """Find notes matching a time range filter."""
        pass
    
    @abstractmethod
    def save(self, note: Note) -> None:
        """Save a note (create or update)."""
        pass
    
    @abstractmethod
    def delete(self, note_id: NoteId) -> None:
        """Delete a note."""
        pass
    
    @abstractmethod
    def exists(self, note_id: NoteId) -> bool:
        """Check if a note exists."""
        pass


class RemoteNoteRepository(ABC):
    """Repository interface for remote notes on device."""
    
    @abstractmethod
    def list_remote_notes(self, directory: str = "") -> List[Note]:
        """List notes available on the remote device."""
        pass
    
    @abstractmethod
    def download_note(self, path: NotePath, local_path: NotePath) -> bool:
        """Download a note from the remote device."""
        pass
    
    @abstractmethod
    def get_remote_checksum(self, path: NotePath) -> Optional[str]:
        """Get the checksum of a remote note."""
        pass