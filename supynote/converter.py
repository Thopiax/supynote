import os
import sys
from pathlib import Path
from typing import Optional, List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import supernotelib as sn
except ImportError:
    print("❌ Error: supernotelib is required for PDF conversion")
    print("Install it with: uv add supernotelib")
    sys.exit(1)


class PDFConverter:
    """Handles conversion of Supernote .note files to PDF format."""
    
    def __init__(self, vectorize: bool = True, enable_links: bool = True):
        """
        Initialize PDF converter.
        
        Args:
            vectorize: Use vector format for high-quality output (default: True)
            enable_links: Enable hyperlinks in PDF output (default: True)
        """
        self.vectorize = vectorize
        self.enable_links = enable_links
    
    def _validate_note_file(self, input_path: Path) -> tuple[bool, str]:
        """
        Validate a .note file before conversion.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not input_path.exists():
            return False, f"File not found: {input_path}"
            
        if not input_path.suffix.lower() == '.note':
            return False, f"Invalid file format: {input_path}. Expected .note file"
        
        # Check file size - very small files are likely corrupted
        file_size = input_path.stat().st_size
        if file_size < 100:  # Less than 100 bytes is likely corrupted
            return False, f"File appears corrupted (too small: {file_size} bytes)"

        # Try to load notebook to check if it's valid
        try:
            notebook = sn.load_notebook(str(input_path), policy='loose')
            if notebook is None:
                return False, "Failed to load notebook (file may be corrupted)"
            
            # Check if we can get basic info without errors
            total_pages = notebook.get_total_pages()
            if total_pages is None:
                return False, "Cannot determine page count (file may be corrupted)"
                
            return True, ""
            
        except Exception as e:
            return False, f"File validation failed: {str(e)}"

    def convert_file(self, input_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None, skip_existing: bool = True) -> bool:
        """
        Convert a single .note file to PDF with robust error handling.
        
        Args:
            input_path: Path to the .note file
            output_path: Output PDF path (optional, defaults to same name with .pdf extension)
            
        Returns:
            True if conversion successful, False otherwise
        """
        input_path = Path(input_path)
        
        # Validate the file first
        is_valid, error_msg = self._validate_note_file(input_path)
        if not is_valid:
            print(f"❌ {error_msg}")
            return False
        
        if output_path is None:
            output_path = input_path.with_suffix('.pdf')
        else:
            output_path = Path(output_path)
        
        # Skip if PDF already exists and is newer
        if output_path.exists():
            input_mtime = input_path.stat().st_mtime
            output_mtime = output_path.stat().st_mtime
            if output_mtime > input_mtime and skip_existing:
                print(f"⏭️ Skipping {input_path.name} (PDF is newer)")
                return True
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"🔄 Converting {input_path.name} to PDF...")
            
            # Load the notebook (already validated above)
            notebook = sn.load_notebook(str(input_path), policy='loose')
            total_pages = notebook.get_total_pages()
            
            if total_pages == 0:
                print(f"⚠️ Warning: {input_path.name} contains no pages, skipping")
                return False
            
            print(f"📄 Processing {total_pages} page(s)...")
            
            # Create PDF converter with error handling
            try:
                converter = sn.converter.PdfConverter(notebook)
            except Exception as e:
                print(f"❌ Failed to create PDF converter for {input_path.name}: {e}")
                return False
            
            # Convert all pages to a single PDF (use -1 for all pages)
            try:
                pdf_content = converter.convert(
                    page_number=-1,
                    vectorize=self.vectorize,
                    enable_link=self.enable_links
                )
                
                if pdf_content is None or len(pdf_content) == 0:
                    print(f"❌ Conversion produced empty PDF for {input_path.name}")
                    return False
                    
            except Exception as e:
                print(f"❌ PDF conversion failed for {input_path.name}: {e}")
                return False
            
            # Write to file with error handling
            try:
                with open(output_path, 'wb') as f:
                    f.write(pdf_content)
            except Exception as e:
                print(f"❌ Failed to write PDF file {output_path}: {e}")
                return False
            
            print(f"✅ Successfully converted to {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Unexpected error converting {input_path.name}: {e}")
            return False
    
    def convert_directory(self, input_dir: Union[str, Path], output_dir: Optional[Union[str, Path]] = None, recursive: bool = True, max_workers: int = 4) -> tuple[int, int]:
        """
        Convert all .note files in a directory to PDF with parallel processing.
        
        Args:
            input_dir: Directory containing .note files
            output_dir: Output directory for PDFs (optional, defaults to same directory)
            recursive: Search subdirectories (default: True)
            max_workers: Maximum number of parallel conversion workers (default: 4)
            
        Returns:
            Tuple of (successful_conversions, total_files)
        """
        input_dir = Path(input_dir)
        
        if not input_dir.exists() or not input_dir.is_dir():
            print(f"❌ Directory not found: {input_dir}")
            return 0, 0
        
        if output_dir is None:
            output_dir = input_dir
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all .note files
        pattern = "**/*.note" if recursive else "*.note"
        note_files = list(input_dir.glob(pattern))
        
        if not note_files:
            print(f"❌ No .note files found in {input_dir}")
            return 0, 0
        
        print(f"📁 Converting {len(note_files)} .note file(s) with {max_workers} workers")
        
        # Prepare conversion tasks
        conversion_tasks = []
        for note_file in note_files:
            # Calculate relative path to maintain directory structure
            rel_path = note_file.relative_to(input_dir)
            output_file = output_dir / rel_path.with_suffix('.pdf')
            conversion_tasks.append((note_file, output_file))
        
        # Process conversions in parallel
        successful = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all conversion jobs
            future_to_file = {
                executor.submit(self.convert_file, note_file, output_file): note_file
                for note_file, output_file in conversion_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                note_file = future_to_file[future]
                try:
                    if future.result():
                        successful += 1
                except Exception as e:
                    print(f"❌ Error converting {note_file.name}: {e}")
        
        print(f"🎉 Converted {successful}/{len(note_files)} files successfully")
        return successful, len(note_files)
    
    def convert_files_batch(self, file_paths: List[Union[str, Path]], output_dir: Optional[Union[str, Path]] = None, max_workers: int = 4) -> tuple[int, int]:
        """
        Convert a list of .note files to PDF with parallel processing.
        
        Args:
            file_paths: List of .note file paths to convert
            output_dir: Output directory for PDFs (optional, defaults to same directory as source)
            max_workers: Maximum number of parallel conversion workers (default: 4)
            
        Returns:
            Tuple of (successful_conversions, total_files)
        """
        if not file_paths:
            return 0, 0
        
        # Filter to only .note files
        note_files = [Path(f) for f in file_paths if Path(f).suffix.lower() == '.note' and Path(f).exists()]
        
        if not note_files:
            print(f"❌ No valid .note files found in provided list")
            return 0, 0
        
        print(f"📁 Converting {len(note_files)} .note file(s) with {max_workers} workers")
        
        # Prepare conversion tasks
        conversion_tasks = []
        for note_file in note_files:
            if output_dir:
                output_path = Path(output_dir) / note_file.with_suffix('.pdf').name
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = note_file.with_suffix('.pdf')
            conversion_tasks.append((note_file, output_path))
        
        # Process conversions in parallel
        successful = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all conversion jobs
            future_to_file = {
                executor.submit(self.convert_file, note_file, output_file): note_file
                for note_file, output_file in conversion_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                note_file = future_to_file[future]
                try:
                    if future.result():
                        successful += 1
                except Exception as e:
                    print(f"❌ Error converting {note_file.name}: {e}")
        
        print(f"🎉 Converted {successful}/{len(note_files)} files successfully")
        return successful, len(note_files)
    
    def get_note_info(self, note_path: Union[str, Path]) -> Optional[dict]:
        """
        Get information about a .note file.
        
        Args:
            note_path: Path to the .note file
            
        Returns:
            Dictionary with file information or None if error
        """
        note_path = Path(note_path)
        
        if not note_path.exists() or note_path.suffix.lower() != '.note':
            return None
        
        try:
            notebook = sn.load_notebook(str(note_path), policy='loose')
            
            return {
                "file_path": str(note_path),
                "file_size": note_path.stat().st_size,
                "total_pages": notebook.get_total_pages(),
                "creation_time": notebook.get_creation_time() if hasattr(notebook, 'get_creation_time') else None,
                "modification_time": notebook.get_modification_time() if hasattr(notebook, 'get_modification_time') else None,
            }
        except Exception as e:
            print(f"❌ Error reading {note_path.name}: {e}")
            return None