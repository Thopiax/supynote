"""PDF processing for adding invisible text layers."""

import fitz
from pathlib import Path
from typing import List

from .entities import PDFPage, TextBlock


class PDFTextLayerProcessor:
    """Processor for adding invisible text layers to PDFs."""
    
    def __init__(self):
        pass
    
    def add_invisible_text_layer(self, pdf_path: Path, pages: List[PDFPage], output_path: Path) -> bool:
        """
        Add invisible text layer to PDF for searchability.
        
        Args:
            pdf_path: Path to original PDF
            pages: List of PDFPage objects with OCR results
            output_path: Path for output PDF with text layer
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Open the original PDF
            doc = fitz.open(str(pdf_path))
            
            # Process each page
            for pdf_page in pages:
                if not pdf_page.has_text:
                    continue
                
                page_num = pdf_page.page_number
                if page_num >= doc.page_count:
                    print(f"⚠️ Page {page_num} not found in PDF, skipping")
                    continue
                
                page = doc[page_num]
                
                # Add text annotations for each text block
                for text_block in pdf_page.ocr_result.text_blocks:
                    self._add_invisible_text_annotation(page, text_block)
            
            # Save the PDF with text layer
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=4, deflate=True)
            doc.close()
            
            print(f"✅ Created searchable PDF: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating searchable PDF: {e}")
            return False
    
    def _add_invisible_text_annotation(self, page: fitz.Page, text_block: TextBlock):
        """Add invisible text annotation to a PDF page."""
        x, y, w, h = text_block.bbox
        
        # Create rectangle for text placement
        rect = fitz.Rect(x, y, x + w, y + h)
        
        # Calculate appropriate font size based on text block height
        font_size = max(8, min(72, h * 0.8))  # Betlween 8pt and 72pt
        
        # Add invisible text annotation
        try:
            # e text at the detected location
            page.insert_text(
                point=(x, y + h * 0.8),  # Position text near bottom of detected region
                text=text_block.text,
                fontsize=font_size,
                color=(1, 1, 1),  # White text (invisible on white background)
                render_mode=3,    # Invisible text mode
                fontname="helv"   # Standard font
            )
        except Exception as e:
            # Fallback: try with different parameters
            try:
                page.insert_text(
                    point=(x, y + h * 0.8),
                    text=text_block.text,
                    fontsize=12,
                    color=(1, 1, 1),
                    render_mode=3,
                    fontname="helv"
                )
            except Exception as e2:
                print(f"⚠️ Failed to add text annotation: {e2}")
    
    def extract_existing_text(self, pdf_path: Path) -> List[str]:
        """
        Extract any existing text from PDF pages.
        Useful for checking if OCR is needed.
        
        Returns:
            List of text content per page
        """
        try:
            doc = fitz.open(str(pdf_path))
            page_texts = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text().strip()
                page_texts.append(text)
            
            doc.close()
            return page_texts
            
        except Exception as e:
            print(f"❌ Error extracting existing text: {e}")
            return []
    
    def has_searchable_text(self, pdf_path: Path) -> bool:
        """Check if PDF already contains searchable text."""
        existing_texts = self.extract_existing_text(pdf_path)
        
        # Consider PDF searchable if any page has substantial text
        for text in existing_texts:
            if len(text.strip()) > 10:  # Arbitrary threshold
                return True
        
        return False