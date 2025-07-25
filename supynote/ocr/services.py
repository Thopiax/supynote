"""Application services and interfaces for OCR processing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Protocol
import time

from .entities import PDFPage, OCRResult, TextBlock


class OCRService(Protocol):
    """Interface for OCR service implementations."""
    
    def extract_text(self, image_path: Path, page_width: float, page_height: float) -> OCRResult:
        """Extract text from an image and return positioned results."""
        ...
    
    @property
    def name(self) -> str:
        """Get the name of this OCR service."""
        ...


class PDFProcessor(Protocol):
    """Interface for PDF processing implementations."""
    
    def add_invisible_text_layer(self, pdf_path: Path, pages: List[PDFPage], output_path: Path) -> bool:
        """Add invisible text layer to PDF."""
        ...


class ProcessPDFUseCase:
    """Use case for processing PDFs with OCR and adding searchable text layers."""
    
    def __init__(self, ocr_service: OCRService, pdf_processor: PDFProcessor):
        self.ocr_service = ocr_service
        self.pdf_processor = pdf_processor
    
    def process_pdf(self, 
                   input_path: Path, 
                   output_path: Path,
                   progress_callback: Optional[callable] = None) -> List[PDFPage]:
        """
        Process a PDF with OCR and create searchable output.
        
        Args:
            input_path: Path to input PDF
            output_path: Path for output PDF with text layer
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of processed PDF pages
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input PDF not found: {input_path}")
        
        # Import here to avoid circular imports
        import fitz
        
        start_time = time.time()
        doc = fitz.open(str(input_path))
        total_pages = doc.page_count
        
        if progress_callback:
            progress_callback(0, total_pages, f"Starting OCR processing...")
        
        processed_pages = []
        
        try:
            for page_num in range(total_pages):
                page_start = time.time()
                
                if progress_callback:
                    progress_callback(page_num, total_pages, f"Processing page {page_num + 1}")
                
                page = doc[page_num]
                page_rect = page.rect
                page_width, page_height = page_rect.width, page_rect.height
                
                # Convert page to high-resolution image for OCR
                matrix = fitz.Matrix(3, 3)  # 3x scaling for better OCR accuracy
                pix = page.get_pixmap(matrix=matrix)
                
                # Save to temporary file
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    pix.save(tmp_file.name)
                    temp_path = Path(tmp_file.name)
                
                try:
                    # Perform OCR
                    ocr_result = self.ocr_service.extract_text(temp_path, page_width, page_height)
                    ocr_result.processing_time = time.time() - page_start
                    
                    # Create PDF page object
                    pdf_page = PDFPage(
                        page_number=page_num,
                        original_pdf_path=input_path,
                        ocr_result=ocr_result
                    )
                    
                    processed_pages.append(pdf_page)
                    
                    if progress_callback:
                        text_count = len(ocr_result.text_blocks)
                        progress_callback(page_num + 1, total_pages, 
                                        f"Page {page_num + 1}: Found {text_count} text blocks")
                
                finally:
                    # Clean up temporary file
                    os.unlink(temp_path)
            
        finally:
            doc.close()
        
        # Add invisible text layer to PDF
        if progress_callback:
            progress_callback(total_pages, total_pages, "Creating searchable PDF...")
        
        success = self.pdf_processor.add_invisible_text_layer(input_path, processed_pages, output_path)
        
        if not success:
            raise RuntimeError(f"Failed to create searchable PDF: {output_path}")
        
        total_time = time.time() - start_time
        
        if progress_callback:
            progress_callback(total_pages, total_pages, 
                            f"Completed in {total_time:.1f}s - {output_path.name}")
        
        return processed_pages
    
    def process_batch(self, 
                     input_dir: Path, 
                     output_dir: Path,
                     max_workers: int = 4,
                     progress_callback: Optional[callable] = None) -> tuple[int, int]:
        """
        Process multiple PDFs in parallel.
        
        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory for output files
            max_workers: Maximum number of parallel workers
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (successful_conversions, total_files)
        """
        if not input_dir.exists() or not input_dir.is_dir():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # Find all PDF files
        pdf_files = list(input_dir.glob("**/*.pdf"))
        
        if not pdf_files:
            if progress_callback:
                progress_callback(0, 0, "No PDF files found")
            return 0, 0
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        successful = 0
        total_files = len(pdf_files)
        
        if progress_callback:
            progress_callback(0, total_files, f"Processing {total_files} PDF files...")
        
        # For now, process sequentially (parallel processing would require more complex progress tracking)
        for i, pdf_file in enumerate(pdf_files):
            try:
                output_file = output_dir / f"{pdf_file.stem}_searchable.pdf"
                
                def file_progress(page_num, total_pages, message):
                    if progress_callback:
                        overall_progress = f"File {i+1}/{total_files}: {message}"
                        progress_callback(i, total_files, overall_progress)
                
                self.process_pdf(pdf_file, output_file, file_progress)
                successful += 1
                
                if progress_callback:
                    progress_callback(i + 1, total_files, f"Completed {pdf_file.name}")
                    
            except Exception as e:
                if progress_callback:
                    progress_callback(i + 1, total_files, f"Failed {pdf_file.name}: {str(e)}")
        
        return successful, total_files