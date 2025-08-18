"""Native Supernote text extraction service using supernotelib."""

import time
from pathlib import Path
from typing import List, Optional

from .entities import OCRResult, TextBlock

try:
    import supernotelib as sn
    SUPERNOTELIB_AVAILABLE = True
except ImportError:
    SUPERNOTELIB_AVAILABLE = False


class NativeSupernoteService:
    """Service for extracting native text from Supernote files using supernotelib."""
    
    def __init__(self):
        if not SUPERNOTELIB_AVAILABLE:
            raise ImportError("supernotelib not available. Install with: uv add supernotelib")
        self.documents_with_warnings = {}  # Track documents with text recognition warnings
    
    def extract_text_from_note(self, note_path: Path) -> List[str]:
        """
        Extract text from a .note file, returning text per page.
        
        Args:
            note_path: Path to the .note file
            
        Returns:
            List of text strings, one per page
        """
        if not note_path.exists() or note_path.suffix.lower() != '.note':
            raise ValueError(f"Invalid .note file: {note_path}")
        
        try:
            # Load the notebook
            notebook = sn.load_notebook(str(note_path))
            total_pages = notebook.get_total_pages()
            
            # Use TextConverter which is the proper way to extract text
            converter = sn.converter.TextConverter(notebook)
            
            page_texts = []
            
            for page_num in range(total_pages):
                try:
                    # Convert page to text using TextConverter
                    page_text = converter.convert(page_num)
                    if page_text is None:
                        page_text = ""
                    page_texts.append(page_text.strip())
                    
                except Exception as e:
                    print(f"⚠️ Warning: Could not extract text from page {page_num + 1}: {e}")
                    page_texts.append("")
            
            return page_texts
            
        except Exception as e:
            print(f"❌ Error loading notebook {note_path.name}: {e}")
            return []
    
    def extract_positioned_text_from_note(self, note_path: Path) -> List[List[dict]]:
        """
        Extract text with precise positioning from a .note file.
        
        Args:
            note_path: Path to the .note file
            
        Returns:
            List of pages, each containing list of positioned text elements
        """
        if not note_path.exists() or note_path.suffix.lower() != '.note':
            raise ValueError(f"Invalid .note file: {note_path}")
        
        try:
            import base64
            import json
            
            # Load the notebook
            notebook = sn.load_notebook(str(note_path))
            total_pages = notebook.get_total_pages()
            
            page_elements = []
            
            for page_num in range(total_pages):
                try:
                    page = notebook.get_page(page_num)
                    recogn_status = page.get_recogn_status()
                    
                    if recogn_status != 1:
                        print(f"⚠️ {note_path.name} - Page {page_num + 1}: Text recognition not completed (status: {recogn_status})")
                        # Track this document as having warnings
                        if str(note_path) not in self.documents_with_warnings:
                            self.documents_with_warnings[str(note_path)] = []
                        self.documents_with_warnings[str(note_path)].append(f"Page {page_num + 1}: status={recogn_status}")
                        page_elements.append([])
                        continue
                    
                    # Get the recognition text (base64 encoded JSON)
                    recogn_text = page.get_recogn_text()
                    if not recogn_text:
                        page_elements.append([])
                        continue
                    
                    # Decode base64 and parse JSON
                    decoded = base64.b64decode(recogn_text).decode('utf-8')
                    data = json.loads(decoded)
                    
                    # Extract positioned words
                    positioned_elements = []
                    if 'elements' in data:
                        for element in data['elements']:
                            if 'words' in element:
                                for word in element['words']:
                                    if 'bounding-box' in word and 'label' in word:
                                        bbox = word['bounding-box']
                                        positioned_elements.append({
                                            'text': word['label'],
                                            'x': bbox['x'],
                                            'y': bbox['y'],
                                            'width': bbox['width'], 
                                            'height': bbox['height']
                                        })
                    
                    page_elements.append(positioned_elements)
                    
                except Exception as e:
                    print(f"⚠️ Warning: Could not extract positioned text from page {page_num + 1}: {e}")
                    page_elements.append([])
            
            return page_elements
            
        except Exception as e:
            print(f"❌ Error loading notebook {note_path.name}: {e}")
            return []
    
    def convert_note_to_searchable_pdf(self, 
                                     note_path: Path, 
                                     output_path: Path,
                                     progress_callback: Optional[callable] = None,
                                     existing_pdf_path: Optional[Path] = None) -> bool:
        """
        Convert a .note file to a searchable PDF using native text extraction.
        
        Args:
            note_path: Path to input .note file
            output_path: Path for output searchable PDF
            progress_callback: Optional progress callback
            existing_pdf_path: Optional path to existing PDF (avoids reconversion)
            
        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()
        
        if progress_callback:
            progress_callback(0, 100, f"Loading {note_path.name}...")
        
        try:
            # Use existing PDF if provided, otherwise convert
            if existing_pdf_path and existing_pdf_path.exists():
                temp_pdf_path = existing_pdf_path
                if progress_callback:
                    progress_callback(25, 100, "Using existing PDF...")
            else:
                # Only convert if we don't have an existing PDF
                from ..converter import PDFConverter
                
                # Create a temporary PDF first
                temp_pdf_path = output_path.with_suffix('.temp.pdf')
                
                converter = PDFConverter(vectorize=True, enable_links=True)
                if not converter.convert_file(note_path, temp_pdf_path):
                    print(f"❌ Failed to convert {note_path.name} to PDF")
                    return False
            
            if progress_callback:
                progress_callback(30, 100, "Extracting native text...")
            
            # Extract native text per page
            page_texts = self.extract_text_from_note(note_path)
            
            if not page_texts:
                print(f"⚠️ No text extracted from {note_path.name}")
                # Still create the PDF without text layer
                temp_pdf_path.rename(output_path)
                return True
            
            if progress_callback:
                progress_callback(50, 100, f"Found text on {len([t for t in page_texts if t])} pages")
            
            # Extract positioned text for precise placement
            if progress_callback:
                progress_callback(60, 100, "Extracting text positioning...")
            
            positioned_elements = self.extract_positioned_text_from_note(note_path)
            
            # Add invisible text layer to the PDF
            if progress_callback:
                progress_callback(80, 100, "Adding precisely positioned text layer...")
            
            # Store note path for coordinate transformation
            self._current_note_path = note_path
            success = self._add_positioned_text_to_pdf(temp_pdf_path, positioned_elements, output_path)
            
            # Clean up temporary file only if we created it
            if not existing_pdf_path and temp_pdf_path.exists() and temp_pdf_path.suffix == '.pdf':
                temp_pdf_path.unlink()
            
            if success:
                # Also create a Markdown file with the extracted text
                if progress_callback:
                    progress_callback(90, 100, "Creating Markdown text file...")
                
                self._create_markdown_file(note_path, page_texts, output_path)
                
                total_time = time.time() - start_time
                if progress_callback:
                    progress_callback(100, 100, f"Completed in {total_time:.1f}s")
                print(f"✅ Created searchable PDF: {output_path}")
                return True
            else:
                print(f"❌ Failed to add text layer to {output_path}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing {note_path.name}: {e}")
            return False
    
    def get_warning_summary(self) -> dict:
        """Get summary of documents with text recognition warnings."""
        return dict(self.documents_with_warnings)
    
    def clear_warnings(self):
        """Clear the warnings tracking."""
        self.documents_with_warnings.clear()
    
    def save_warning_report(self, output_path: Path):
        """Save warning report to a file."""
        if not self.documents_with_warnings:
            return
        
        with open(output_path, 'w') as f:
            f.write("OCR Text Recognition Warning Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total documents with warnings: {len(self.documents_with_warnings)}\n\n")
            
            for doc_path, warnings in sorted(self.documents_with_warnings.items()):
                filename = Path(doc_path).name
                f.write(f"📄 {filename}\n")
                f.write(f"   Path: {doc_path}\n")
                f.write(f"   Warnings:\n")
                for warning in warnings:
                    f.write(f"   - {warning}\n")
                f.write("\n")
    
    def _add_native_text_to_pdf(self, pdf_path: Path, page_texts: List[str], output_path: Path) -> bool:
        """Add native text as invisible layer to PDF with proper positioning and sizing."""
        try:
            import fitz
            
            # Open the PDF
            doc = fitz.open(str(pdf_path))
            
            for page_num, text in enumerate(page_texts):
                if page_num >= doc.page_count:
                    break
                
                if not text.strip():
                    continue
                
                page = doc[page_num]
                page_rect = page.rect
                
                # Add invisible text with better positioning and sizing
                try:
                    # Split text into lines
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    if not lines:
                        continue
                    
                    # Calculate positioning to cover the content area (with margins)
                    margin_left = page_rect.width * 0.08  # 8% left margin
                    margin_top = page_rect.height * 0.12  # 12% top margin
                    content_width = page_rect.width * 0.84  # 84% of page width
                    content_height = page_rect.height * 0.76  # 76% of page height
                    
                    # Calculate line spacing and font size based on content density
                    num_lines = len(lines)
                    if num_lines > 0:
                        line_spacing = content_height / max(num_lines, 1)
                        # Font size should be proportional to line spacing but reasonable
                        font_size = min(max(line_spacing * 0.6, 10), 18)
                    else:
                        line_spacing = 20
                        font_size = 12
                    
                    # Place each line with proper spacing
                    for i, line in enumerate(lines):
                        if line:
                            y_pos = margin_top + (i * line_spacing) + (font_size * 0.8)
                            
                            # Ensure we don't go beyond page boundaries
                            if y_pos > page_rect.height - margin_top:
                                break
                            
                            try:
                                page.insert_text(
                                    point=(margin_left, y_pos),
                                    text=line,
                                    fontsize=font_size,
                                    color=(1, 1, 1),  # White (invisible on white background)
                                    render_mode=3,    # Invisible text mode
                                    fontname="helv"   # Standard font
                                )
                            except Exception as line_error:
                                # Try with smaller font if insertion fails
                                try:
                                    page.insert_text(
                                        point=(margin_left, y_pos),
                                        text=line,
                                        fontsize=10,
                                        color=(1, 1, 1),
                                        render_mode=3,
                                        fontname="helv"
                                    )
                                except Exception:
                                    print(f"⚠️ Could not add line {i+1} on page {page_num + 1}: {line_error}")
                            
                except Exception as e:
                    print(f"⚠️ Warning: Could not add text to page {page_num + 1}: {e}")
            
            # Save the searchable PDF
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=4, deflate=True)
            doc.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding text layer: {e}")
            return False
    
    def _add_positioned_text_to_pdf(self, pdf_path: Path, positioned_elements: List[List[dict]], output_path: Path) -> bool:
        """Add native text with exact positioning using bounding box data."""
        try:
            import fitz
            
            # Load the original notebook to get Supernote dimensions
            notebook = sn.load_notebook(str(self._current_note_path))
            supernote_width = notebook.get_width()
            supernote_height = notebook.get_height()
            
            # Open the PDF
            doc = fitz.open(str(pdf_path))
            
            for page_num, elements in enumerate(positioned_elements):
                if page_num >= doc.page_count:
                    break
                
                if not elements:
                    continue
                
                page = doc[page_num]
                page_rect = page.rect
                
                # Calculate coordinate ranges to understand the content area
                if elements:
                    x_coords = [e['x'] for e in elements]
                    y_coords = [e['y'] for e in elements]
                    content_x_min, content_x_max = min(x_coords), max(x_coords)
                    content_y_min, content_y_max = min(y_coords), max(y_coords)
                    content_width = content_x_max - content_x_min
                    content_height = content_y_max - content_y_min
                else:
                    content_x_min = content_y_min = 0
                    content_width = content_height = 1
                
                # Try direct mapping without artificial margins - let the natural Supernote layout determine positioning
                pdf_margin_x = 0    # No artificial margins
                pdf_margin_y = 0    
                pdf_content_width = page_rect.width
                pdf_content_height = page_rect.height
                
                print(f"📍 Adding {len(elements)} positioned text elements to page {page_num + 1}")
                print(f"   Content area: Supernote ({content_x_min:.1f},{content_y_min:.1f}) to ({content_x_max:.1f},{content_y_max:.1f})")
                print(f"   PDF margins: {pdf_margin_x:.1f}x{pdf_margin_y:.1f}, content: {pdf_content_width:.1f}x{pdf_content_height:.1f}")
                
                # Add each text element at its scaled position
                for element in elements:
                    try:
                        text = element['text']
                        if not text.strip():
                            continue
                        
                        # Get Supernote coordinates
                        sn_x = element['x']
                        sn_y = element['y'] 
                        sn_width = element['width']
                        sn_height = element['height']
                        
                        # Map from Supernote content area to PDF content area
                        if content_width > 0 and content_height > 0:
                            # Normalize coordinates within the content area (0-1)
                            norm_x = (sn_x - content_x_min) / content_width if content_width > 0 else 0
                            norm_y = (sn_y - content_y_min) / content_height if content_height > 0 else 0
                            norm_width = sn_width / content_width if content_width > 0 else 0
                            norm_height = sn_height / content_height if content_height > 0 else 0
                            
                            # Map to PDF content area with fine-tuning offsets
                            pdf_x = pdf_margin_x + (norm_x * pdf_content_width)
                            pdf_y = pdf_margin_y + (norm_y * pdf_content_height)
                            pdf_width = norm_width * pdf_content_width
                            pdf_height = norm_height * pdf_content_height
                            
                            # Fine-tuning adjustments: relative to text size and position
                            pdf_x += pdf_width * 0.15   # Move right by 15% of text width
                            pdf_y -= pdf_height * 0.25  # Move up by 25% of text height
                        else:
                            # Fallback to simple scaling
                            x_scale = page_rect.width / supernote_width
                            y_scale = page_rect.height / supernote_height
                            pdf_x = sn_x * x_scale
                            pdf_y = sn_y * y_scale
                            pdf_width = sn_width * x_scale
                            pdf_height = sn_height * y_scale
                            
                            # Apply same relative adjustments
                            pdf_x += pdf_width * 0.15   # Move right by 15% of text width
                            pdf_y -= pdf_height * 0.25  # Move up by 25% of text height
                        
                        # Calculate font size based on the scaled bounding box height
                        font_size = max(pdf_height * 0.8, 8)  # Minimum 8pt font
                        font_size = min(font_size, 24)        # Maximum 24pt font
                        
                        # Position text at the scaled location
                        # Y coordinate adjustment for baseline positioning
                        text_y = pdf_y + pdf_height * 0.8
                        
                        page.insert_text(
                            point=(pdf_x, text_y),
                            text=text,
                            fontsize=font_size,
                            color=(1, 1, 1),  # White (invisible)
                            render_mode=3,    # Invisible text mode
                            fontname="helv"   # Standard font
                        )
                        
                    except Exception as e:
                        print(f"⚠️ Warning: Could not place text '{element.get('text', '')}' at position ({element.get('x', 0)}, {element.get('y', 0)}): {e}")
            
            # Save the searchable PDF
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=4, deflate=True)
            doc.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding positioned text layer: {e}")
            return False
    
    def _create_markdown_file(self, note_path: Path, page_texts: List[str], pdf_output_path: Path):
        """Create a Markdown file with the extracted text, organized by pages."""
        try:
            # Create markdown file path (same name as PDF but with .md extension)
            md_path = pdf_output_path.with_suffix('.md')
            
            # Get note metadata
            from datetime import datetime
            note_name = note_path.stem
            creation_date = datetime.fromtimestamp(note_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            
            # Build markdown content
            markdown_content = []
            
            # Add front matter / header
            markdown_content.append(f"# {note_name}")
            markdown_content.append(f"")
            markdown_content.append(f"**Source:** `{note_path.name}`  ")
            markdown_content.append(f"**Created:** {creation_date}  ")
            markdown_content.append(f"**Total Pages:** {len(page_texts)}  ")
            markdown_content.append(f"**Searchable PDF:** `{pdf_output_path.name}`")
            markdown_content.append(f"")
            markdown_content.append("---")
            markdown_content.append("")
            
            # Add each page with clear separation
            for page_num, text in enumerate(page_texts):
                if text.strip():  # Only add pages with text
                    markdown_content.append(f"## Page {page_num + 1}")
                    markdown_content.append("")
                    
                    # Format the text, preserving structure
                    formatted_text = self._format_text_for_markdown(text)
                    markdown_content.append(formatted_text)
                    markdown_content.append("")
                    markdown_content.append("---")
                    markdown_content.append("")
            
            # Write to file
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(markdown_content))
            
            print(f"📝 Created Markdown file: {md_path}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not create Markdown file: {e}")
    
    def _format_text_for_markdown(self, text: str) -> str:
        """Format extracted text for better Markdown presentation."""
        if not text.strip():
            return ""
        
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect and format moment markers
            if line.startswith('(m.') or line.startswith('Fm.') or line.startswith('m.'):
                # Make moment markers bold
                formatted_lines.append(f"**{line}**")
            elif line.startswith('- '):
                # Keep bullet points as-is
                formatted_lines.append(line)
            elif line.startswith('↳') or line.startswith('⤷'):
                # Format sub-bullets with proper indentation
                formatted_lines.append(f"  {line}")
            else:
                # Regular text
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def extract_text(self, note_path: Path, page_width: float, page_height: float) -> OCRResult:
        """
        Extract text from .note file - compatibility method for OCR interface.
        Note: This is for .note files, not image files like other OCR services.
        """
        start_time = time.time()
        
        # This method is mainly for interface compatibility
        # The actual work is done in convert_note_to_searchable_pdf
        page_texts = self.extract_text_from_note(note_path)
        
        text_blocks = []
        
        if page_texts:
            # Combine all pages into one block for this interface
            full_text = '\n\n'.join(text for text in page_texts if text.strip())
            
            if full_text.strip():
                text_block = TextBlock(
                    text=full_text,
                    confidence=1.0,  # Native text has perfect confidence
                    bbox=(0, 0, page_width, page_height),
                    normalized_bbox=(0, 0, 1, 1)
                )
                text_blocks.append(text_block)
        
        processing_time = time.time() - start_time
        
        return OCRResult(
            page_number=0,
            text_blocks=text_blocks,
            page_width=page_width,
            page_height=page_height,
            processing_time=processing_time
        )
    
    @property
    def name(self) -> str:
        return "Native Supernote Text"