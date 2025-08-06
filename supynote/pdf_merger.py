#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

try:
    from pypdf import PdfWriter
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def _extract_date_from_filename(file_path: Path) -> Optional[datetime]:
    """
    Extract creation date from filename or metadata.
    Supports formats like: YYYYMMDD_HHMMSS.pdf or YYYYMMDD_HHMMSS.note
    """
    filename = file_path.stem  # Remove extension
    
    # Try to parse YYYYMMDD_HHMMSS format
    if re.match(r'^\d{8}_\d{6}', filename):
        date_part = filename[:15]  # YYYYMMDD_HHMMSS
        try:
            return datetime.strptime(date_part, '%Y%m%d_%H%M%S')
        except ValueError:
            pass
    
    # If filename parsing fails, try to find corresponding .note file
    note_file = file_path.with_suffix('.note')
    if note_file.exists() and note_file != file_path:
        return _extract_date_from_filename(note_file)
    
    # Try to extract from .note metadata if this is a .note file
    if file_path.suffix.lower() == '.note':
        try:
            import supernotelib as sn
            notebook = sn.load_notebook(str(file_path))
            if notebook:
                metadata = notebook.get_metadata()
                # Check if metadata has timestamp info
                if hasattr(metadata, 'header') and hasattr(metadata.header, 'created_time'):
                    # Convert timestamp to datetime if available
                    return datetime.fromtimestamp(metadata.header.created_time)
        except:
            pass
    
    # Fallback to file modification time
    return datetime.fromtimestamp(file_path.stat().st_mtime)


def merge_pdfs_by_date(directory: Path, time_range: str = "all") -> None:
    """
    Merge PDF files in a directory by their actual creation date, creating one PDF per date.
    Files are sorted by time within each date. Only includes files within the specified time range.
    
    Args:
        directory: Directory containing PDF files to merge
        time_range: Time range filter (week, 2weeks, month, all)
    """
    if not PYPDF_AVAILABLE:
        print("❌ PyPDF not available. Run: uv add pypdf")
        return
    
    # Find all PDF files, excluding the merged_by_date directory
    all_pdf_files = list(directory.glob("**/*.pdf"))
    # Exclude files in the merged_by_date directory
    pdf_files = [f for f in all_pdf_files if "merged_by_date" not in str(f)]
    
    if not pdf_files:
        print("❌ No PDF files found to merge")
        return
    
    # Calculate cutoff date for filtering
    now = datetime.now()
    if time_range == "week":
        cutoff = now - timedelta(days=7)
    elif time_range == "2weeks":
        cutoff = now - timedelta(days=14)
    elif time_range == "month":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = None  # Include all files
    
    # Group files by date
    files_by_date: Dict[str, List[tuple[Path, datetime]]] = {}
    skipped_by_time = 0
    
    for pdf_file in pdf_files:
        # Extract actual creation date from filename
        creation_date = _extract_date_from_filename(pdf_file)
        
        # Apply time range filter
        if cutoff and creation_date < cutoff:
            skipped_by_time += 1
            continue
            
        file_date = creation_date.strftime("%Y-%m-%d")
        
        if file_date not in files_by_date:
            files_by_date[file_date] = []
        files_by_date[file_date].append((pdf_file, creation_date))
    
    if not files_by_date:
        if skipped_by_time > 0:
            print(f"✅ No files to merge ({skipped_by_time} files outside time range: {time_range})")
        else:
            print("✅ No files to merge")
        return
    
    # Create merged directory
    merged_dir = directory / "merged_by_date"
    merged_dir.mkdir(exist_ok=True)
    
    total_files = sum(len(file_list) for file_list in files_by_date.values())
    print(f"📚 Merging {total_files} PDFs into {len(files_by_date)} date-based files...")
    if skipped_by_time > 0:
        print(f"⏭️ Skipped {skipped_by_time} files outside time range: {time_range}")
    
    # Merge PDFs for each date
    for date_str, date_files in sorted(files_by_date.items()):
        # Sort files by creation time within the date (using the datetime we extracted)
        date_files.sort(key=lambda item: item[1])  # item[1] is the datetime
        
        output_file = merged_dir / f"{date_str}.pdf"
        
        if output_file.exists():
            print(f"🔄 Overwriting {date_str}.pdf with updated content...")
        else:
            print(f"📝 Creating {date_str}.pdf with {len(date_files)} files...")
        
        merger = PdfWriter()
        
        for pdf_file, creation_date in date_files:
            try:
                merger.append(str(pdf_file))
                print(f"  ✅ Added {pdf_file.name} ({creation_date.strftime('%H:%M:%S')})")
            except Exception as e:
                print(f"  ❌ Error adding {pdf_file.name}: {e}")
        
        # Write the merged PDF
        try:
            with open(output_file, 'wb') as output:
                merger.write(output)
            print(f"✅ Created {output_file.name}")
        except Exception as e:
            print(f"❌ Error writing {output_file.name}: {e}")
        finally:
            merger.close()
    
    print(f"🎉 Merged PDFs saved to {merged_dir}")
    print(f"📊 Summary: {total_files} files merged into {len(files_by_date)} date-based PDFs")
    
    # List the final merged files
    final_merged = sorted(merged_dir.glob("*.pdf"))
    if final_merged:
        print(f"\n📁 Merged files in {merged_dir.name}/:")
        for pdf in final_merged:
            size_mb = pdf.stat().st_size / (1024 * 1024)
            print(f"  📄 {pdf.name} ({size_mb:.1f} MB)")


def merge_pdfs_with_custom_names(pdf_files: List[Path], output_file: Path) -> bool:
    """
    Merge multiple PDF files into a single PDF.
    
    Args:
        pdf_files: List of PDF file paths to merge
        output_file: Output file path for merged PDF
        
    Returns:
        True if successful, False otherwise
    """
    if not PYPDF_AVAILABLE:
        print("❌ PyPDF not available. Run: uv add pypdf")
        return False
    
    try:
        merger = PdfWriter()
        
        for pdf_file in pdf_files:
            if pdf_file.exists():
                merger.append(str(pdf_file))
            else:
                print(f"⚠️ File not found: {pdf_file}")
        
        with open(output_file, 'wb') as output:
            merger.write(output)
        
        merger.close()
        return True
        
    except Exception as e:
        print(f"❌ Error merging PDFs: {e}")
        return False