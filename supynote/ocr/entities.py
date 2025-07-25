"""Domain entities for OCR processing."""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path


@dataclass
class TextBlock:
    """Represents a block of recognized text with positioning information."""
    text: str
    confidence: float
    # Bounding box in PDF coordinate space (x, y, width, height)
    bbox: Tuple[float, float, float, float]
    # Original normalized coordinates from OCR service (0-1 range)
    normalized_bbox: Optional[Tuple[float, float, float, float]] = None


@dataclass
class OCRResult:
    """Result of OCR processing for a single page."""
    page_number: int
    text_blocks: List[TextBlock]
    page_width: float
    page_height: float
    processing_time: Optional[float] = None
    
    @property
    def full_text(self) -> str:
        """Get all text concatenated with line breaks."""
        return '\n'.join(block.text for block in self.text_blocks)
    
    @property
    def confidence_score(self) -> float:
        """Get average confidence score for all text blocks."""
        if not self.text_blocks:
            return 0.0
        return sum(block.confidence for block in self.text_blocks) / len(self.text_blocks)


@dataclass
class PDFPage:
    """Represents a PDF page with OCR results."""
    page_number: int
    original_pdf_path: Path
    ocr_result: Optional[OCRResult] = None
    
    @property
    def has_text(self) -> bool:
        """Check if page has recognized text."""
        return self.ocr_result is not None and len(self.ocr_result.text_blocks) > 0