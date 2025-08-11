#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
from dataclasses import dataclass

try:
    from pypdf import PdfWriter
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import supernotelib as sn
    SUPERNOTELIB_AVAILABLE = True
except ImportError:
    SUPERNOTELIB_AVAILABLE = False


@dataclass
class MergeConfig:
    """Configuration for merging operations."""
    pdf_output_dir: str = "pdf_notes"
    markdown_output_dir: str = "markdown_notes"
    time_range: str = "all"  # week, 2weeks, month, all
    merge_by_date: bool = True


class DateBasedMerger:
    """Handles merging of PDFs and Markdown files by date."""
    
    def __init__(self, config: MergeConfig = None):
        self.config = config or MergeConfig()
    
    def _extract_date_from_file(self, file_path: Path) -> Optional[datetime]:
        """
        Extract creation date from filename or metadata.
        Supports formats like: YYYYMMDD_HHMMSS
        """
        filename = file_path.stem
        
        # Try to parse YYYYMMDD_HHMMSS format
        if re.match(r'^\d{8}_\d{6}', filename):
            date_part = filename[:15]
            try:
                return datetime.strptime(date_part, '%Y%m%d_%H%M%S')
            except ValueError:
                pass
        
        # If it's a .note file, try to extract from metadata
        if file_path.suffix.lower() == '.note' and SUPERNOTELIB_AVAILABLE:
            try:
                notebook = sn.load_notebook(str(file_path))
                if notebook:
                    metadata = notebook.get_metadata()
                    if hasattr(metadata, 'header') and hasattr(metadata.header, 'created_time'):
                        return datetime.fromtimestamp(metadata.header.created_time)
            except:
                pass
        
        # For PDFs, check if there's a corresponding .note file
        if file_path.suffix.lower() == '.pdf':
            note_file = file_path.with_suffix('.note')
            if note_file.exists():
                return self._extract_date_from_file(note_file)
        
        # Fallback to file modification time
        return datetime.fromtimestamp(file_path.stat().st_mtime)
    
    def _get_time_cutoff(self) -> Optional[datetime]:
        """Calculate cutoff date based on time range."""
        if self.config.time_range == "all":
            return None
        
        now = datetime.now()
        if self.config.time_range == "week":
            return now - timedelta(days=7)
        elif self.config.time_range == "2weeks":
            return now - timedelta(days=14)
        elif self.config.time_range == "month":
            return now - timedelta(days=30)
        return None
    
    def _group_files_by_date(self, files: List[Path]) -> Dict[str, List[Tuple[Path, datetime]]]:
        """Group files by date, filtering by time range."""
        files_by_date: Dict[str, List[Tuple[Path, datetime]]] = {}
        cutoff = self._get_time_cutoff()
        skipped = 0
        
        for file_path in files:
            # Extract date
            file_date = self._extract_date_from_file(file_path)
            
            # Apply time filter
            if cutoff and file_date < cutoff:
                skipped += 1
                continue
            
            date_str = file_date.strftime("%Y-%m-%d")
            
            if date_str not in files_by_date:
                files_by_date[date_str] = []
            files_by_date[date_str].append((file_path, file_date))
        
        # Sort files within each date by time
        for date_str in files_by_date:
            files_by_date[date_str].sort(key=lambda x: x[1])
        
        return files_by_date, skipped
    
    def merge_pdfs_by_date(self, directory: Path) -> None:
        """
        Merge PDF files by date into the configured output directory.
        """
        if not PYPDF_AVAILABLE:
            print("❌ PyPDF not available. Run: uv add pypdf")
            return
        
        # Find all PDF files, excluding output directories
        all_pdfs = list(directory.glob("**/*.pdf"))
        pdf_files = [
            f for f in all_pdfs 
            if self.config.pdf_output_dir not in str(f) and 
               self.config.markdown_output_dir not in str(f) and
               "merged_by_date" not in str(f)
        ]
        
        if not pdf_files:
            print("❌ No PDF files found to merge")
            return
        
        # Group by date
        files_by_date, skipped = self._group_files_by_date(pdf_files)
        
        if not files_by_date:
            if skipped > 0:
                print(f"✅ No PDFs to merge ({skipped} files outside {self.config.time_range} range)")
            else:
                print("✅ No PDFs to merge")
            return
        
        # Create output directory
        output_dir = directory / self.config.pdf_output_dir
        output_dir.mkdir(exist_ok=True)
        
        total_files = sum(len(files) for files in files_by_date.values())
        print(f"📚 Merging {total_files} PDFs into {len(files_by_date)} date-based files...")
        if skipped > 0:
            print(f"⏭️ Skipped {skipped} files outside {self.config.time_range} range")
        
        # Merge PDFs for each date
        for date_str, date_files in sorted(files_by_date.items()):
            output_file = output_dir / f"{date_str}.pdf"
            
            if output_file.exists():
                print(f"🔄 Updating {date_str}.pdf...")
            else:
                print(f"📝 Creating {date_str}.pdf with {len(date_files)} files...")
            
            merger = PdfWriter()
            
            for pdf_file, creation_time in date_files:
                try:
                    merger.append(str(pdf_file))
                    time_str = creation_time.strftime('%H:%M:%S')
                    print(f"  ✅ Added {pdf_file.name} ({time_str})")
                except Exception as e:
                    print(f"  ❌ Error adding {pdf_file.name}: {e}")
            
            # Write merged PDF
            try:
                with open(output_file, 'wb') as output:
                    merger.write(output)
                print(f"✅ Created {output_file.name}")
            except Exception as e:
                print(f"❌ Error writing {output_file.name}: {e}")
            finally:
                merger.close()
        
        print(f"🎉 Merged PDFs saved to {output_dir}")
        self._print_summary(output_dir)
    
    def _extract_text_from_note(self, note_path: Path) -> Optional[str]:
        """Extract text content from a .note file."""
        if not SUPERNOTELIB_AVAILABLE:
            return None
        
        try:
            notebook = sn.load_notebook(str(note_path))
            converter = sn.converter.TextConverter(notebook)
            
            all_text = []
            total_pages = notebook.get_total_pages()
            
            for page_num in range(total_pages):
                try:
                    page_text = converter.convert(page_num)
                    if page_text:
                        all_text.append(page_text)
                except:
                    continue
            
            return "\n\n---\n\n".join(all_text) if all_text else None
        except:
            return None
    
    
    def merge_markdown_by_date(self, directory: Path) -> None:
        """
        Create markdown files by date from .note files only.
        """
        # Find all .note files
        note_files = list(directory.glob("**/*.note"))
        
        # Exclude output directories
        note_files = [
            f for f in note_files 
            if self.config.pdf_output_dir not in str(f) and 
               self.config.markdown_output_dir not in str(f)
        ]
        
        all_files = note_files
        
        if not all_files:
            print("❌ No files found to create markdown from")
            return
        
        # Group by date
        files_by_date, skipped = self._group_files_by_date(all_files)
        
        if not files_by_date:
            if skipped > 0:
                print(f"✅ No files to process ({skipped} files outside {self.config.time_range} range)")
            else:
                print("✅ No files to process")
            return
        
        # Create output directory
        output_dir = directory / self.config.markdown_output_dir
        output_dir.mkdir(exist_ok=True)
        
        total_files = sum(len(files) for files in files_by_date.values())
        print(f"📝 Creating {len(files_by_date)} markdown files from {total_files} source files...")
        if skipped > 0:
            print(f"⏭️ Skipped {skipped} files outside {self.config.time_range} range")
        
        # Create markdown for each date
        for date_str, date_files in sorted(files_by_date.items()):
            output_file = output_dir / f"{date_str}.md"
            
            if output_file.exists():
                print(f"🔄 Updating {date_str}.md...")
            else:
                print(f"📝 Creating {date_str}.md with {len(date_files)} files...")
            
            markdown_content = [f"# Notes for {date_str}\n"]
            
            for file_path, creation_time in date_files:
                time_str = creation_time.strftime('%H:%M:%S')
                markdown_content.append(f"\n## {file_path.name} ({time_str})\n")
                
                # Extract text from .note file
                text_content = self._extract_text_from_note(file_path)
                if text_content:
                    print(f"  ✅ Extracted text from {file_path.name}")
                    markdown_content.append(text_content)
                else:
                    print(f"  ⏭️ No text in {file_path.name}")
                    markdown_content.append(f"*No text content available for {file_path.name}*")
            
            # Write markdown file
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(markdown_content))
                print(f"✅ Created {output_file.name}")
            except Exception as e:
                print(f"❌ Error writing {output_file.name}: {e}")
        
        print(f"🎉 Markdown files saved to {output_dir}")
        self._print_summary(output_dir)
    
    def merge_all_by_date(self, directory: Path) -> None:
        """
        Merge both PDFs and create markdown files by date.
        """
        print("🚀 Starting date-based merge operation...")
        print(f"📅 Time range: {self.config.time_range}")
        print(f"📁 PDF output: {self.config.pdf_output_dir}/")
        print(f"📁 Markdown output: {self.config.markdown_output_dir}/")
        print()
        
        # Merge PDFs
        print("=" * 50)
        print("PDF MERGING")
        print("=" * 50)
        self.merge_pdfs_by_date(directory)
        
        print()
        
        # Create markdown files
        print("=" * 50)
        print("MARKDOWN CREATION")
        print("=" * 50)
        self.merge_markdown_by_date(directory)
        
        print()
        print("✨ All merge operations completed!")
    
    def _print_summary(self, output_dir: Path) -> None:
        """Print summary of files in output directory."""
        files = sorted(output_dir.glob("*"))
        if files:
            print(f"\n📊 Summary - {len(files)} files in {output_dir.name}/:")
            total_size = 0
            for file in files[:10]:  # Show first 10 files
                size_mb = file.stat().st_size / (1024 * 1024)
                total_size += size_mb
                print(f"  📄 {file.name} ({size_mb:.1f} MB)")
            if len(files) > 10:
                print(f"  ... and {len(files) - 10} more files")
            print(f"  💾 Total size: {total_size:.1f} MB")