"""Note aggregate root."""

from datetime import datetime
from typing import Optional
from enum import Enum

from ...shared.base_entity import AggregateRoot, DomainEvent
from ..value_objects.note_id import NoteId
from ..value_objects.note_path import NotePath


class SyncStatus(Enum):
    """Sync status for a note."""
    NOT_SYNCED = "not_synced"
    SYNCING = "syncing"
    SYNCED = "synced"
    MODIFIED = "modified"
    ERROR = "error"


class ConversionStatus(Enum):
    """Conversion status for a note."""
    NOT_CONVERTED = "not_converted"
    CONVERTING = "converting"
    CONVERTED = "converted"
    ERROR = "error"


# Domain Events
class NoteCreated(DomainEvent):
    """Event raised when a note is created."""
    def __init__(self, note_id: NoteId, path: NotePath):
        super().__init__()
        self.note_id = note_id
        self.path = path


class NoteSynced(DomainEvent):
    """Event raised when a note is synced."""
    def __init__(self, note_id: NoteId):
        super().__init__()
        self.note_id = note_id


class NoteConvertedToPDF(DomainEvent):
    """Event raised when a note is converted to PDF."""
    def __init__(self, note_id: NoteId, pdf_path: NotePath):
        super().__init__()
        self.note_id = note_id
        self.pdf_path = pdf_path


class Note(AggregateRoot):
    """Note aggregate root representing a Supernote file."""
    
    def __init__(
        self,
        note_id: NoteId,
        path: NotePath,
        created_at: datetime,
        modified_at: datetime,
        size: int = 0,
        checksum: Optional[str] = None
    ):
        super().__init__(note_id)
        self._path = path
        self._created_at = created_at
        self._modified_at = modified_at
        self._size = size
        self._checksum = checksum
        self._sync_status = SyncStatus.NOT_SYNCED
        self._conversion_status = ConversionStatus.NOT_CONVERTED
        self._last_synced_at: Optional[datetime] = None
        self._remote_checksum: Optional[str] = None
        self._pdf_path: Optional[NotePath] = None
        self._has_searchable_text = False
        
        self._raise_event(NoteCreated(note_id, path))
    
    @classmethod
    def create_from_remote(
        cls,
        path: NotePath,
        created_at: datetime,
        modified_at: datetime,
        size: int,
        checksum: Optional[str] = None
    ) -> 'Note':
        """Factory method to create a note from remote device info."""
        note_id = NoteId.from_path(path.full_path)
        return cls(note_id, path, created_at, modified_at, size, checksum)
    
    @property
    def path(self) -> NotePath:
        """Get the note's path."""
        return self._path
    
    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at
    
    @property
    def modified_at(self) -> datetime:
        """Get modification timestamp."""
        return self._modified_at
    
    @property
    def size(self) -> int:
        """Get file size in bytes."""
        return self._size
    
    @property
    def sync_status(self) -> SyncStatus:
        """Get current sync status."""
        return self._sync_status
    
    @property
    def conversion_status(self) -> ConversionStatus:
        """Get current conversion status."""
        return self._conversion_status
    
    @property
    def pdf_path(self) -> Optional[NotePath]:
        """Get the PDF path if converted."""
        return self._pdf_path
    
    def needs_sync(self, remote_checksum: Optional[str] = None) -> bool:
        """Check if this note needs to be synced."""
        if self._sync_status == SyncStatus.NOT_SYNCED:
            return True
        
        if self._sync_status == SyncStatus.ERROR:
            return True
        
        if remote_checksum and self._checksum != remote_checksum:
            return True
        
        return False
    
    def mark_as_syncing(self) -> None:
        """Mark the note as currently syncing."""
        if self._sync_status == SyncStatus.SYNCING:
            raise ValueError("Note is already syncing")
        self._sync_status = SyncStatus.SYNCING
    
    def mark_as_synced(self, checksum: str) -> None:
        """Mark the note as successfully synced."""
        self._sync_status = SyncStatus.SYNCED
        self._last_synced_at = datetime.now()
        self._remote_checksum = checksum
        self._checksum = checksum
        self._raise_event(NoteSynced(self.id))
    
    def mark_sync_error(self, error_message: str) -> None:
        """Mark sync as failed."""
        self._sync_status = SyncStatus.ERROR
        # Could store error message if needed
    
    def needs_conversion(self) -> bool:
        """Check if this note needs PDF conversion."""
        return (self._path.is_note_file() and 
                self._conversion_status in [ConversionStatus.NOT_CONVERTED, ConversionStatus.ERROR])
    
    def mark_as_converting(self) -> None:
        """Mark the note as currently converting."""
        if self._conversion_status == ConversionStatus.CONVERTING:
            raise ValueError("Note is already converting")
        self._conversion_status = ConversionStatus.CONVERTING
    
    def mark_as_converted(self, pdf_path: NotePath) -> None:
        """Mark the note as successfully converted to PDF."""
        self._conversion_status = ConversionStatus.CONVERTED
        self._pdf_path = pdf_path
        self._raise_event(NoteConvertedToPDF(self.id, pdf_path))
    
    def mark_conversion_error(self, error_message: str) -> None:
        """Mark conversion as failed."""
        self._conversion_status = ConversionStatus.ERROR
        # Could store error message if needed
    
    def needs_ocr(self) -> bool:
        """Check if this note needs OCR processing."""
        return (self._conversion_status == ConversionStatus.CONVERTED and 
                not self._has_searchable_text)
    
    def mark_as_searchable(self) -> None:
        """Mark the note's PDF as having searchable text."""
        if self._conversion_status != ConversionStatus.CONVERTED:
            raise ValueError("Cannot mark as searchable without PDF conversion")
        self._has_searchable_text = True
    
    def is_within_time_range(self, cutoff_date: Optional[datetime]) -> bool:
        """Check if note is within the specified time range."""
        if cutoff_date is None:
            return True
        return self._created_at >= cutoff_date
    
    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"Note(id={self.id}, path={self._path}, sync={self._sync_status.value})"