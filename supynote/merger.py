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
    journals_dir: Optional[Path] = None  # Optional directory to copy markdown files to
    assets_dir: Optional[Path] = None  # Optional directory to copy PDFs to (e.g., Logseq assets)


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
        output_dir.mkdir(parents=True, exist_ok=True)
        
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
    
    def _extract_text_from_note(self, note_path: Path) -> Optional[List[str]]:
        """Extract text content from a .note file, returning pages as separate list items."""
        if not SUPERNOTELIB_AVAILABLE:
            return None

        try:
            notebook = sn.load_notebook(str(note_path))
            converter = sn.converter.TextConverter(notebook)

            all_pages = []
            total_pages = notebook.get_total_pages()

            for page_num in range(total_pages):
                try:
                    page_text = converter.convert(page_num)
                    if page_text:
                        all_pages.append(page_text)
                except:
                    continue

            return all_pages if all_pages else None
        except:
            return None

    def _detect_moments(self, pages: List[str]) -> List[Tuple[Optional[str], List[str]]]:
        """
        Parse pages and group them by 'moment' pattern.
        Returns list of (moment_title, content_lines) tuples.
        Moment title is detected by pattern: ^-?\s*[mM][eE]?\s*\.?\s*\d+
        Matches: m. 7, M. 8, me 10, - m. 5, ME. 3, etc.
        """
        moments = []
        current_moment_title = None
        current_moment_content = []

        # More permissive pattern: optional dash/bullet, m/M/me/ME, optional dot, spaces, digits
        moment_pattern = re.compile(r'^-?\s*[mM][eE]?\s*\.?\s*\d+')

        for page in pages:
            lines = page.strip().split('\n')

            # Check if first line is a moment marker
            if lines and moment_pattern.match(lines[0].strip()):
                # Save previous moment if exists
                if current_moment_content:
                    moments.append((current_moment_title, current_moment_content))

                # Start new moment
                first_line = lines[0].strip()
                first_line = re.sub(r'^-\s*', '', first_line)  # Remove leading dash

                # Check if there's a dash anywhere in the line (indicating bullet content)
                if ' - ' in first_line or ' -' in first_line:
                    # Find the first occurrence of ' -' (dash with space before or after)
                    dash_idx = first_line.find(' -')
                    if dash_idx > 0:
                        # Split on the dash
                        current_moment_title = first_line[:dash_idx].strip()
                        content_after_dash = first_line[dash_idx+1:].strip()  # Skip the space and dash
                        if content_after_dash:
                            current_moment_content = [content_after_dash] + [line for line in lines[1:] if line.strip()]
                        else:
                            current_moment_content = [line for line in lines[1:] if line.strip()]
                    else:
                        # Shouldn't happen but fallback
                        current_moment_title = first_line
                        current_moment_content = [line for line in lines[1:] if line.strip()]
                else:
                    # No dash, keep whole line as title
                    current_moment_title = first_line
                    current_moment_content = [line for line in lines[1:] if line.strip()]
            else:
                # Continue current moment
                current_moment_content.extend([line for line in lines if line.strip()])

        # Add the last moment
        if current_moment_content:
            moments.append((current_moment_title, current_moment_content))

        return moments

    def _format_text_as_bullets(self, lines: List[str], indent_level: int = 1) -> str:
        """
        Convert text lines to Logseq-style bullets.
        indent_level: number of indentation levels (1 = 4 spaces)

        Handles:
        - Lines starting with '-' or '*' as bullet points
        - Lines starting with '↳' as sub-bullets (indented one level deeper)
        - Lines without markers are continuations of the previous bullet/sub-bullet
        """
        if not lines:
            return ""

        base_indent = "    " * indent_level
        bullets = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if it's a sub-bullet marker (↳)
            if line.startswith('↳'):
                sub_text = line[1:].strip()
                # Remove any leading bullet marker from sub-text
                sub_text = re.sub(r'^[-*]\s+', '', sub_text)
                if sub_text:
                    bullets.append(f"{base_indent}    - {sub_text}")
                continue

            # Check if line starts with a bullet marker
            if re.match(r'^[-*]\s+', line):
                # Remove the bullet marker and create new bullet
                text = re.sub(r'^[-*]\s+', '', line)
                bullets.append(f"{base_indent}- {text}")
            else:
                # This is a continuation of the previous bullet
                if bullets:
                    bullets[-1] = f"{bullets[-1]} {line}"
                else:
                    # No previous bullet, create a new one
                    bullets.append(f"{base_indent}- {line}")

        return '\n'.join(bullets)


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
        output_dir.mkdir(parents=True, exist_ok=True)
        
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

            markdown_content = []

            for file_path, creation_time in date_files:
                # Extract pages from .note file
                pages = self._extract_text_from_note(file_path)

                if not pages:
                    print(f"  ⏭️ No text in {file_path.name}")
                    continue

                print(f"  ✅ Extracted text from {file_path.name}")

                # Process each page as its own section
                moment_pattern = re.compile(r'^-?\s*[mM][oOeE]?\s*\.?\s*\d+')

                for page_text in pages:
                    lines = page_text.strip().split('\n')
                    if not lines or not any(line.strip() for line in lines):
                        continue

                    first_line = lines[0].strip()
                    first_line = re.sub(r'^-\s*', '', first_line)  # Remove leading dash

                    # Check if first line is a moment marker
                    if moment_pattern.match(first_line):
                        # Check if there's a dash in the line (indicating bullet content)
                        if ' - ' in first_line or ' -' in first_line:
                            dash_idx = first_line.find(' -')
                            if dash_idx > 0:
                                # Split on the dash
                                moment_title = first_line[:dash_idx].strip()
                                content_after_dash = first_line[dash_idx+1:].strip()

                                # Add moment heading
                                markdown_content.append(f"- ## {moment_title}")

                                # Format content starting with text after dash
                                content_lines = [content_after_dash] + [line for line in lines[1:] if line.strip()]
                                bullets = self._format_text_as_bullets(content_lines)
                                if bullets:
                                    markdown_content.append(bullets)
                            else:
                                # Shouldn't happen but fallback
                                markdown_content.append(f"- ## {first_line}")
                                content_lines = [line for line in lines[1:] if line.strip()]
                                bullets = self._format_text_as_bullets(content_lines)
                                if bullets:
                                    markdown_content.append(bullets)
                        else:
                            # No dash, whole first line is title
                            markdown_content.append(f"- ## {first_line}")
                            content_lines = [line for line in lines[1:] if line.strip()]
                            bullets = self._format_text_as_bullets(content_lines)
                            if bullets:
                                markdown_content.append(bullets)
                    else:
                        # No moment marker, just format all lines as bullets
                        content_lines = [line for line in lines if line.strip()]
                        bullets = self._format_text_as_bullets(content_lines)
                        if bullets:
                            markdown_content.append(bullets)

            # Add PDF link if PDF exists
            if markdown_content:  # Only add if there's content
                pdf_output_dir = directory / self.config.pdf_output_dir
                pdf_file = pdf_output_dir / f"{date_str}.pdf"

                if pdf_file.exists():
                    # Copy PDF to assets directory if configured
                    if self.config.assets_dir:
                        import shutil
                        assets_path = Path(self.config.assets_dir)
                        assets_path.mkdir(parents=True, exist_ok=True)
                        assets_pdf = assets_path / f"{date_str}.pdf"
                        shutil.copy2(pdf_file, assets_pdf)
                        print(f"  📎 Copied PDF to assets: {assets_pdf.name}")

                        # Use assets-relative path (works in Logseq)
                        markdown_content.insert(0, f"- 📄 [View PDF](../assets/{date_str}.pdf)")
                    elif self.config.journals_dir:
                        # Fallback: compute relative path from journals directory to PDF
                        import os
                        journals_path = Path(self.config.journals_dir)
                        try:
                            rel_path = os.path.relpath(pdf_file, journals_path)
                            markdown_content.insert(0, f"- 📄 [View PDF]({rel_path})")
                        except ValueError:
                            # Paths on different drives, use absolute path as fallback
                            markdown_content.insert(0, f"- 📄 [View PDF](file://{pdf_file})")

            # Write markdown file
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    # Join with single newline between sections
                    f.write('\n'.join(markdown_content))
                print(f"✅ Created {output_file.name}")
                
                # Copy to journals directory if configured
                if self.config.journals_dir:
                    journals_path = Path(self.config.journals_dir)
                    if journals_path.exists():
                        journal_file = journals_path / output_file.name
                        if not journal_file.exists():
                            import shutil
                            shutil.copy2(output_file, journal_file)
                            print(f"  📔 Copied to journals: {journal_file}")
                        else:
                            print(f"  ⏭️ Journal entry already exists: {journal_file.name}")
                    else:
                        print(f"  ⚠️ Journals directory not found: {journals_path}")
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