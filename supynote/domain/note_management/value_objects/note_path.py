"""Note path value object."""

from pathlib import Path
from typing import Optional

from ...shared.base_value_object import ValueObject


class NotePath(ValueObject):
    """Represents the path to a note file."""
    
    def __init__(self, directory: str, filename: str):
        self._validate_directory(directory)
        self._validate_filename(filename)
        self._directory = directory
        self._filename = filename
    
    @classmethod
    def from_string(cls, path_str: str) -> 'NotePath':
        """Create from a path string like 'Note/file.note'."""
        path = Path(path_str)
        directory = str(path.parent) if path.parent != Path('.') else ''
        filename = path.name
        return cls(directory, filename)
    
    @property
    def directory(self) -> str:
        """Get the directory part."""
        return self._directory
    
    @property
    def filename(self) -> str:
        """Get the filename part."""
        return self._filename
    
    @property
    def full_path(self) -> str:
        """Get the full path as a string."""
        if self._directory:
            return f"{self._directory}/{self._filename}"
        return self._filename
    
    @property
    def value(self) -> str:
        """Get the full path value."""
        return self.full_path
    
    def with_extension(self, ext: str) -> 'NotePath':
        """Create a new NotePath with a different extension."""
        if not ext.startswith('.'):
            ext = f'.{ext}'
        stem = Path(self._filename).stem
        new_filename = f"{stem}{ext}"
        return NotePath(self._directory, new_filename)
    
    def is_note_file(self) -> bool:
        """Check if this is a .note file."""
        return self._filename.lower().endswith('.note')
    
    def is_pdf_file(self) -> bool:
        """Check if this is a .pdf file."""
        return self._filename.lower().endswith('.pdf')
    
    def _validate_directory(self, directory: str) -> None:
        """Validate directory path."""
        if directory and '..' in directory:
            raise ValueError("Directory path cannot contain '..'")
    
    def _validate_filename(self, filename: str) -> None:
        """Validate filename."""
        if not filename:
            raise ValueError("Filename cannot be empty")
        if '/' in filename or '\\' in filename:
            raise ValueError("Filename cannot contain path separators")
    
    def __eq__(self, other: object) -> bool:
        """Paths are equal if directory and filename match."""
        if not isinstance(other, NotePath):
            return False
        return (self._directory == other._directory and 
                self._filename == other._filename)
    
    def __hash__(self) -> int:
        """Hash based on full path."""
        return hash((self._directory, self._filename))
    
    def __str__(self) -> str:
        """String representation."""
        return self.full_path
    
    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"NotePath('{self._directory}', '{self._filename}')"