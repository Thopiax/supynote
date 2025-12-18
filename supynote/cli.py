#!/usr/bin/env python3

import argparse
import webbrowser
from pathlib import Path
import os

from .device_finder import find_device
from .supernote import Supernote
from .converter import PDFConverter


def get_optimal_workers():
    """Get optimal worker count based on CPU cores."""
    try:
        cpu_count = os.cpu_count() or 4
        # For M4 Pro and similar high-performance systems, be more aggressive
        # Use 2x CPU cores for I/O bound tasks (downloads), capped at 30
        download_workers = min(cpu_count * 2, 30)
        # Use CPU cores for CPU-bound tasks (conversion/OCR), capped at 16
        conversion_workers = min(cpu_count, 16)
        return download_workers, conversion_workers
    except:
        return 20, 8  # Reasonable defaults


def main():
    parser = argparse.ArgumentParser(
        description="Simple CLI tool to interact with Supernote devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  supynote find                    # Find Supernote device on network
  supynote browse                  # Open device web interface
  supynote list                    # List all files on device
  supynote list Note               # List files in Note directory
  supynote download Note           # Download Note directory
  supynote download Note/file.note # Download specific file
  supynote convert file.note       # Convert .note file to PDF
  supynote convert Note/           # Convert all .note files in directory
  supynote ocr file.note           # Create searchable PDF from .note (native text)
  supynote ocr handwritten.pdf --engine llava  # OCR handwritten PDF with LLaVA
  supynote ocr notes/ --batch      # Batch process .note files to searchable PDFs
  supynote merge                   # Merge PDFs and create markdown by date
  supynote merge --time-range week # Merge only files from last week
  supynote merge --pdf-only        # Only merge PDFs, skip markdown
        """
    )
    
    parser.add_argument("--ip", help="Supernote device IP address")
    parser.add_argument("--port", default="8089", help="Device port (default: 8089)")
    parser.add_argument("--output", "-o", help="Local output directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output including skip messages")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Find command
    find_parser = subparsers.add_parser("find", help="Find Supernote device on network")
    find_parser.add_argument("--open", action="store_true", help="Open device in browser")
    
    # Browse command  
    subparsers.add_parser("browse", help="Open device web interface in browser")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List files on device")
    list_parser.add_argument("directory", nargs="?", default="", help="Directory to list")
    
    # Download command
    default_download_workers, default_conversion_workers = get_optimal_workers()
    download_parser = subparsers.add_parser("download", help="Download files from device")
    download_parser.add_argument("path", help="File or directory path to download")
    download_parser.add_argument("--workers", type=int, default=default_download_workers, 
                                help=f"Number of concurrent downloads (default: {default_download_workers})")
    download_parser.add_argument("--async", dest="use_async", action="store_true", default=True, help="Use high-performance async downloader")
    download_parser.add_argument("--no-async", dest="use_async", action="store_false", help="Use traditional sync downloader")
    download_parser.add_argument("--convert-pdf", dest="convert_pdf", action="store_true", default=True, help="Convert downloaded .note files to PDF (default: enabled)")
    download_parser.add_argument("--no-convert-pdf", dest="convert_pdf", action="store_false", help="Skip PDF conversion")
    download_parser.add_argument("--conversion-workers", type=int, default=default_conversion_workers, 
                                help=f"Number of parallel PDF conversion workers (default: {default_conversion_workers})")
    download_parser.add_argument("--ocr", dest="ocr", action="store_true", default=True, help="Create searchable PDFs using native text extraction (default: enabled)")
    download_parser.add_argument("--no-ocr", dest="ocr", action="store_false", help="Skip OCR processing")
    download_parser.add_argument("--force", action="store_true", help="Force re-download even if files exist locally")
    download_parser.add_argument("--check-size", action="store_true", default=True, help="Skip files if local size matches remote (default: true)")
    download_parser.add_argument("--time-range", choices=["week", "2weeks", "month", "all"], default="all", help="Download files from time range (default: all)")
    download_parser.add_argument("--merge-by-date", dest="merge_by_date", action="store_true", default=True, help="Merge PDFs by date, naming files as YYYY-MM-DD.pdf (default: enabled)")
    download_parser.add_argument("--no-merge", dest="merge_by_date", action="store_false", help="Skip merging PDFs by date")
    download_parser.add_argument("--merge-all", dest="merge_only_timestamped", action="store_false", default=True, help="Merge ALL files by date, not just timestamped ones (default: merge only timestamped)")
    download_parser.add_argument("--processed-output", help="Directory for final processed files (merged PDFs and markdowns)")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert .note files to PDF")
    convert_parser.add_argument("path", help="File or directory path to convert")
    convert_parser.add_argument("--output", "-o", help="Output directory or file path")
    convert_parser.add_argument("--no-vector", action="store_true", help="Disable vector format (use raster)")
    convert_parser.add_argument("--no-links", action="store_true", help="Disable hyperlinks in PDF")
    convert_parser.add_argument("--recursive", "-r", action="store_true", default=True, help="Process subdirectories (default: true)")
    convert_parser.add_argument("--workers", type=int, default=default_conversion_workers, 
                               help=f"Number of parallel conversion workers (default: {default_conversion_workers})")
    
    # Info command
    subparsers.add_parser("info", help="Show device information")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Find corrupted .note files in downloaded directory")
    validate_parser.add_argument("directory", nargs="?", default="./data", help="Directory to validate (default: ./data)")
    validate_parser.add_argument("--workers", type=int, default=default_conversion_workers, 
                                help=f"Number of parallel validation workers (default: {default_conversion_workers})")
    validate_parser.add_argument("--fix", action="store_true", help="Re-download all problematic files (requires device connection)")
    validate_parser.add_argument("--convert", action="store_true", help="Convert re-downloaded files to PDF after fixing")
    
    # OCR command
    ocr_parser = subparsers.add_parser("ocr", help="OCR handwritten PDFs to make them searchable")
    ocr_parser.add_argument("input", help="PDF file or directory to process")
    ocr_parser.add_argument("--output", "-o", help="Output file or directory")
    ocr_parser.add_argument("--batch", action="store_true", help="Process directory of PDFs")
    ocr_parser.add_argument("--workers", type=int, default=default_conversion_workers, 
                           help=f"Number of parallel workers for batch processing (default: {default_conversion_workers})")
    ocr_parser.add_argument("--check-existing", action="store_true", default=True, help="Skip PDFs that already have searchable text")
    ocr_parser.add_argument("--force", action="store_true", help="Process even if PDF already has searchable text")
    ocr_parser.add_argument("--engine", choices=["native", "gemini", "llava", "trocr"], default="native", help="OCR engine to use (default: native)")
    ocr_parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama API URL (default: http://localhost:11434)")
    
    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge PDFs and create markdown files by date")
    merge_parser.add_argument("directory", nargs="?", default="./data", help="Directory to process (default: ./data)")
    merge_parser.add_argument("--pdf-output", default="pdfs", help="Output directory for merged PDFs (default: pdfs)")
    merge_parser.add_argument("--markdown-output", default="markdowns", help="Output directory for markdown files (default: markdowns)")
    merge_parser.add_argument("--time-range", choices=["week", "2weeks", "month", "all"], default="all", help="Time range filter (default: all)")
    merge_parser.add_argument("--pdf-only", action="store_true", help="Only merge PDFs, skip markdown creation")
    merge_parser.add_argument("--markdown-only", action="store_true", help="Only create markdown files, skip PDF merging")
    merge_parser.add_argument("--merge-all", dest="merge_only_timestamped", action="store_false", default=True, help="Merge ALL files by date, not just timestamped ones (default: merge only timestamped)")
    merge_parser.add_argument(
        "--journals-dir",
        default=os.environ.get("SUPYNOTE_JOURNALS_DIR"),
        help="Directory to copy markdown files to (set via SUPYNOTE_JOURNALS_DIR env var or this argument)"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    from .presentation.cli.dispatcher import CommandDispatcher
    result = CommandDispatcher.try_dispatch(args.command, args)

    if not result:
        print("❌ Command could not be dispatched")
        return

    print("✅ Command executed successfully")


if __name__ == "__main__":
    main()