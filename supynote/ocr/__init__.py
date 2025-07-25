"""OCR module for processing handwritten PDFs with searchable text layers."""

from .entities import PDFPage, OCRResult, TextBlock
from .services import OCRService, ProcessPDFUseCase

__all__ = ['PDFPage', 'OCRResult', 'TextBlock', 'OCRService', 'ProcessPDFUseCase']