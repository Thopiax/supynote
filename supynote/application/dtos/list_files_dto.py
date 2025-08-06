"""DTOs for the List Files use case."""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class FileItem:
    """Represents a file or directory item."""
    name: str
    is_directory: bool
    date: Optional[str] = None
    size: Optional[int] = None
    path: Optional[str] = None


@dataclass
class ListFilesRequest:
    """Request DTO for listing files."""
    
    ip: Optional[str] = None
    port: str = "8089"
    directory: str = ""  # Empty string means root


@dataclass
class ListFilesResponse:
    """Response DTO for listing files."""
    
    success: bool
    directory: str = ""
    files: List[FileItem] = None
    message: Optional[str] = None
    
    @classmethod
    def success_with_files(cls, directory: str, files: List[FileItem]) -> "ListFilesResponse":
        """Create a success response with file list."""
        return cls(
            success=True,
            directory=directory or "root",
            files=files or []
        )
    
    @classmethod
    def error(cls, message: str) -> "ListFilesResponse":
        """Create an error response."""
        return cls(
            success=False,
            files=[],
            message=message
        )