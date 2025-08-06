"""Data Transfer Objects for download operations."""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

from ...domain.note_management.value_objects.time_range_filter import TimeRange


class DownloadMode(Enum):
    """Download execution mode."""
    SYNC = "sync"
    ASYNC = "async"


class WorkflowStep(Enum):
    """OCR workflow steps."""
    DOWNLOAD = "download"
    CONVERT = "convert"
    OCR = "ocr"
    MERGE = "merge"


@dataclass
class DownloadNotesRequest:
    """Request DTO for downloading notes."""
    path: str
    output_directory: Optional[str] = None
    force: bool = False
    check_size: bool = True
    time_range: TimeRange = TimeRange.ALL
    max_workers: int = 20
    download_mode: DownloadMode = DownloadMode.ASYNC
    
    # Workflow options
    convert_pdf: bool = False
    enable_ocr: bool = False
    merge_by_date: bool = False
    conversion_workers: int = 8


@dataclass
class DownloadProgress:
    """Progress information for download operations."""
    current: int
    total: int
    current_file: Optional[str] = None
    phase: WorkflowStep = WorkflowStep.DOWNLOAD
    
    @property
    def percentage(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100.0


@dataclass
class WorkflowSummary:
    """Summary of completed workflow steps."""
    downloaded_files: int = 0
    converted_files: int = 0
    ocr_processed_files: int = 0
    merged_pdfs: int = 0
    failed_downloads: int = 0
    failed_conversions: int = 0
    failed_ocr: int = 0
    skipped_files: int = 0


@dataclass
class DownloadNotesResponse:
    """Response DTO for downloading notes."""
    success: bool
    total_files: int
    workflow_summary: WorkflowSummary
    error_message: Optional[str] = None
    
    @classmethod
    def success_response(cls, total_files: int, summary: WorkflowSummary) -> 'DownloadNotesResponse':
        """Create a successful response."""
        return cls(
            success=True,
            total_files=total_files,
            workflow_summary=summary
        )
    
    @classmethod
    def failure_response(cls, error_message: str) -> 'DownloadNotesResponse':
        """Create a failure response."""
        return cls(
            success=False,
            total_files=0,
            workflow_summary=WorkflowSummary(),
            error_message=error_message
        )