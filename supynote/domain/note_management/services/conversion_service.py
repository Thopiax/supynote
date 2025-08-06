"""Domain service for note conversion operations."""

from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

from ..entities.note import Note
from ..value_objects.note_path import NotePath


class ConversionService(ABC):
    """Domain service interface for converting notes to PDF."""
    
    @abstractmethod
    def convert_note(self, note: Note) -> bool:
        """
        Convert a single note to PDF.
        
        Returns True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def convert_notes_batch(self, notes: List[Note], max_workers: int = 8) -> int:
        """
        Convert multiple notes to PDF in parallel.
        
        Returns the number of successfully converted notes.
        """
        pass
    
    @abstractmethod
    def supports_vectorization(self) -> bool:
        """Check if this service supports vector PDF output."""
        pass
    
    @abstractmethod
    def supports_hyperlinks(self) -> bool:
        """Check if this service supports hyperlinks in PDF output."""
        pass


class OCRService(ABC):
    """Domain service interface for OCR processing."""
    
    @abstractmethod
    def make_pdf_searchable(self, note: Note) -> bool:
        """
        Add searchable text layer to a note's PDF.
        
        Requires the note to already be converted to PDF.
        Returns True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def process_notes_batch(self, notes: List[Note], max_workers: int = 8) -> int:
        """
        Process multiple notes for OCR in parallel.
        
        Returns the number of successfully processed notes.
        """
        pass
    
    @abstractmethod
    def supports_native_text_extraction(self) -> bool:
        """Check if this service can extract native text from Supernote files."""
        pass


class MergeService(ABC):
    """Domain service interface for PDF merging operations."""
    
    @abstractmethod
    def merge_pdfs_by_date(
        self, 
        notes: List[Note], 
        output_directory: Path,
        time_range_filter: Optional[str] = None
    ) -> int:
        """
        Merge PDFs grouped by date.
        
        Groups notes by their creation date and merges PDFs for each date.
        Returns the number of merged PDF files created.
        """
        pass
    
    @abstractmethod
    def get_date_grouping(self, notes: List[Note]) -> dict:
        """
        Group notes by date.
        
        Returns a dictionary where keys are date strings (YYYY-MM-DD)
        and values are lists of notes for that date.
        """
        pass