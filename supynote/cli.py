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
    download_parser.add_argument("--convert-pdf", action="store_true", help="Convert downloaded .note files to PDF")
    download_parser.add_argument("--conversion-workers", type=int, default=default_conversion_workers, 
                                help=f"Number of parallel PDF conversion workers (default: {default_conversion_workers})")
    download_parser.add_argument("--ocr", action="store_true", help="Create searchable PDFs using native text extraction (requires --convert-pdf)")
    download_parser.add_argument("--force", action="store_true", help="Force re-download even if files exist locally")
    download_parser.add_argument("--check-size", action="store_true", default=True, help="Skip files if local size matches remote (default: true)")
    download_parser.add_argument("--time-range", choices=["week", "2weeks", "month", "all"], default="all", help="Download files from time range (default: all)")
    download_parser.add_argument("--merge-by-date", action="store_true", help="Merge PDFs by date, naming files as YYYY-MM-DD.pdf")
    
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
    validate_parser.add_argument("directory", nargs="?", default="./supernote_files", help="Directory to validate (default: ./supynote_files)")
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
    merge_parser.add_argument("directory", nargs="?", default="./supernote_files", help="Directory to process (default: ./supernote_files)")
    merge_parser.add_argument("--pdf-output", default="pdf_notes", help="Output directory for merged PDFs (default: pdf_notes)")
    merge_parser.add_argument("--markdown-output", default="markdown_notes", help="Output directory for markdown files (default: markdown_notes)")
    merge_parser.add_argument("--time-range", choices=["week", "2weeks", "month", "all"], default="all", help="Time range filter (default: all)")
    merge_parser.add_argument("--pdf-only", action="store_true", help="Only merge PDFs, skip markdown creation")
    merge_parser.add_argument("--markdown-only", action="store_true", help="Only create markdown files, skip PDF merging")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Try to handle through DDD architecture first
    try:
        from .presentation.cli.dispatcher import CommandDispatcher
        if CommandDispatcher.try_dispatch(args.command, args):
            return
    except ImportError:
        pass  # DDD modules not available, use legacy
    
    # Handle commands that don't need device connection
    if args.command == "find":
        # Legacy implementation (fallback)
        ip = find_device()
        if ip and args.open:
            url = f"http://{ip}:{args.port}"
            print(f"🌐 Opening {url} in browser...")
            webbrowser.open(url)
        return
    
    elif args.command in ["convert", "ocr", "merge"]:
        # These commands work with local files only - no device needed
        pass
    
    else:
        # For device commands, we need a device IP
        ip = args.ip or find_device()
        if not ip:
            print("❌ No Supernote device found. Use --ip to specify manually.")
            return
        
        # Create Supernote instance
        device = Supernote(ip, args.port, args.output)
    
    if args.command == "browse":
        # Legacy implementation (fallback)
        url = f"http://{ip}:{args.port}"
        print(f"🌐 Opening {url} in browser...")
        webbrowser.open(url)
    
    elif args.command == "list":
        data = device.list_files(args.directory)
        if data and "fileList" in data:
            print(f"\n📁 Files in {args.directory or 'root'}:")
            for item in data["fileList"]:
                icon = "📁" if item["isDirectory"] else "📄"
                name = item["name"]
                date = item.get("date", "")
                print(f"  {icon} {name} {date}")
        else:
            print("❌ Could not list files")
    
    elif args.command == "download":
        if args.use_async:
            # Use high-performance async downloader
            async def async_download():
                try:
                    if "/" in args.path and not args.path.endswith("/"):
                        # Downloading a specific file (use sync for single files)
                        success = device.download_file(args.path, force=args.force, check_size=args.check_size)
                        if success and args.convert_pdf and args.path.lower().endswith('.note'):
                            local_file = device.local_root / args.path.lstrip('/')
                            converter = PDFConverter(vectorize=True, enable_links=True)
                            converter.convert_file(local_file)
                            
                            # OCR the converted PDF if requested
                            if args.ocr:
                                pdf_file = local_file.with_suffix('.pdf')
                                if pdf_file.exists():
                                    from .ocr.native_service import NativeSupernoteService
                                    native_service = NativeSupernoteService()
                                    searchable_pdf = pdf_file.with_stem(f"{pdf_file.stem}_searchable")
                                    print(f"🔍 Creating searchable PDF...")
                                    native_service.convert_note_to_searchable_pdf(local_file, searchable_pdf)
                                    # Remove intermediate PDF
                                    pdf_file.unlink()
                                    # Rename searchable PDF to original name
                                    searchable_pdf.rename(pdf_file)
                    else:
                        # Downloading a directory with async
                        success, total = await device.download_directory_async(
                            args.path, args.workers, args.force, args.check_size, 
                            time_range=args.time_range)
                        print(f"🎉 Async download completed: {success}/{total} files")
                        if args.convert_pdf:
                            local_dir = device.local_root / args.path.lstrip('/')
                            converter = PDFConverter(vectorize=True, enable_links=True)
                            converter.convert_directory(local_dir, max_workers=args.conversion_workers, time_range=args.time_range)
                            
                            # OCR the converted PDFs if requested (do this BEFORE merging)
                            if args.ocr:
                                from .ocr.native_service import NativeSupernoteService
                                native_service = NativeSupernoteService()
                                
                                # Find all .note files that were converted
                                note_files = list(local_dir.glob("**/*.note"))
                                print(f"🔍 Creating searchable PDFs for {len(note_files)} files...")
                                
                                from concurrent.futures import ThreadPoolExecutor, as_completed
                                
                                def process_note_for_ocr(note_file):
                                    pdf_file = note_file.with_suffix('.pdf')
                                    if pdf_file.exists():
                                        searchable_pdf = pdf_file.with_stem(f"{pdf_file.stem}_searchable")
                                        # Pass existing PDF to avoid reconversion
                                        success = native_service.convert_note_to_searchable_pdf(
                                            note_file, searchable_pdf, existing_pdf_path=pdf_file)
                                        if success:
                                            # Remove intermediate PDF
                                            pdf_file.unlink()
                                            # Rename searchable PDF to original name
                                            searchable_pdf.rename(pdf_file)
                                            return True
                                    return False
                                
                                successful_ocr = 0
                                with ThreadPoolExecutor(max_workers=args.conversion_workers) as executor:
                                    futures = {executor.submit(process_note_for_ocr, note_file): note_file 
                                              for note_file in note_files}
                                    
                                    for future in as_completed(futures):
                                        if future.result():
                                            successful_ocr += 1
                                
                                print(f"🎉 Created {successful_ocr}/{len(note_files)} searchable PDFs")
                            
                            # Merge searchable PDFs by date if requested (do this AFTER OCR)
                            if args.merge_by_date:
                                from .pdf_merger import merge_pdfs_by_date
                                merge_pdfs_by_date(local_dir, args.time_range)
                finally:
                    await device.close_async()
            
            # Import asyncio and run the async download
            import asyncio
            asyncio.run(async_download())
        else:
            # Use traditional sync downloader
            if "/" in args.path and not args.path.endswith("/"):
                # Downloading a specific file
                success = device.download_file(args.path, force=args.force, check_size=args.check_size)
                if success and args.convert_pdf and args.path.lower().endswith('.note'):
                    local_file = device.local_root / args.path.lstrip('/')
                    converter = PDFConverter(vectorize=True, enable_links=True)
                    converter.convert_file(local_file)
                    
                    # OCR the converted PDF if requested
                    if args.ocr:
                        pdf_file = local_file.with_suffix('.pdf')
                        if pdf_file.exists():
                            from .ocr.native_service import NativeSupernoteService
                            native_service = NativeSupernoteService()
                            searchable_pdf = pdf_file.with_stem(f"{pdf_file.stem}_searchable")
                            print(f"🔍 Creating searchable PDF...")
                            native_service.convert_note_to_searchable_pdf(local_file, searchable_pdf)
                            # Remove intermediate PDF
                            pdf_file.unlink()
                            # Rename searchable PDF to original name
                            searchable_pdf.rename(pdf_file)
            else:
                # Downloading a directory
                success, total = device.download_directory(
                    args.path, args.workers, args.force, args.check_size,
                    time_range=args.time_range)
                print(f"📊 Sync download completed: {success}/{total} files")
                if args.convert_pdf:
                    local_dir = device.local_root / args.path.lstrip('/')
                    converter = PDFConverter(vectorize=True, enable_links=True)
                    converter.convert_directory(local_dir, max_workers=args.conversion_workers, time_range=args.time_range)
                    
                    # OCR the converted PDFs if requested (do this BEFORE merging)
                    if args.ocr:
                        from .ocr.native_service import NativeSupernoteService
                        native_service = NativeSupernoteService()
                        
                        # Find all .note files that were converted
                        note_files = list(local_dir.glob("**/*.note"))
                        print(f"🔍 Creating searchable PDFs for {len(note_files)} files...")
                        
                        from concurrent.futures import ThreadPoolExecutor, as_completed
                        
                        def process_note_for_ocr(note_file):
                            pdf_file = note_file.with_suffix('.pdf')
                            if pdf_file.exists():
                                searchable_pdf = pdf_file.with_stem(f"{pdf_file.stem}_searchable")
                                # Pass existing PDF to avoid reconversion
                                success = native_service.convert_note_to_searchable_pdf(
                                    note_file, searchable_pdf, existing_pdf_path=pdf_file)
                                if success:
                                    # Remove intermediate PDF
                                    pdf_file.unlink()
                                    # Rename searchable PDF to original name
                                    searchable_pdf.rename(pdf_file)
                                    return True
                            return False
                        
                        successful_ocr = 0
                        with ThreadPoolExecutor(max_workers=args.conversion_workers) as executor:
                            futures = {executor.submit(process_note_for_ocr, note_file): note_file 
                                      for note_file in note_files}
                            
                            for future in as_completed(futures):
                                if future.result():
                                    successful_ocr += 1
                        
                        print(f"🎉 Created {successful_ocr}/{len(note_files)} searchable PDFs")
                    
                    # Merge searchable PDFs by date if requested (do this AFTER OCR)
                    if args.merge_by_date:
                        from .pdf_merger import merge_pdfs_by_date
                        merge_pdfs_by_date(local_dir, args.time_range)
    
    elif args.command == "convert":
        # Handle convert command - works with local files only
        input_path = Path(args.path)
        
        if not input_path.exists():
            print(f"❌ Path not found: {input_path}")
            return
        
        # Create converter with user preferences
        converter = PDFConverter(
            vectorize=not args.no_vector,
            enable_links=not args.no_links
        )
        
        if input_path.is_file():
            # Convert single file
            output_path = Path(args.output) if args.output else None
            converter.convert_file(input_path, output_path)
        elif input_path.is_dir():
            # Convert directory with parallel processing
            output_dir = Path(args.output) if args.output else None
            converter.convert_directory(input_path, output_dir, args.recursive, args.workers)
        else:
            print(f"❌ Invalid path: {input_path}")
    
    elif args.command == "info":
        # Legacy implementation (fallback)
        info = device.get_device_info()
        print(f"\n📱 Supernote Device Info:")
        print(f"  IP: {info['ip']}")
        print(f"  Port: {info['port']}")
        print(f"  URL: {info['url']}")
        print(f"  Status: {info['status']}")
        if args.output:
            print(f"  Local directory: {Path(args.output).absolute()}")
    
    elif args.command == "validate":
        # Handle validate command - works with local files only
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import supernotelib as sn
        
        validate_dir = Path(args.directory)
        if not validate_dir.exists():
            print(f"❌ Directory not found: {validate_dir}")
            return
        
        # Find all .note files
        note_files = list(validate_dir.glob("**/*.note"))
        if not note_files:
            print(f"❌ No .note files found in {validate_dir}")
            return
        
        print(f"🔍 Validating {len(note_files)} .note files with {args.workers} workers...")
        
        corrupted_files = []
        unsupported_files = []
        
        def validate_note_file(note_file):
            try:
                # Try to load the notebook with loose policy
                notebook = sn.load_notebook(str(note_file), policy='loose')
                if notebook is None:
                    return note_file, "Failed to load notebook", "corrupted"
                
                # Try to get basic info
                total_pages = notebook.get_total_pages()
                if total_pages is None:
                    return note_file, "Cannot determine page count", "corrupted"
                
                return note_file, None, "valid"  # Success
                
            except Exception as e:
                error_msg = str(e)
                if "unsupported file format" in error_msg.lower():
                    return note_file, error_msg, "unsupported"
                else:
                    return note_file, error_msg, "corrupted"
        
        # Validate files in parallel
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            # Submit all validation jobs
            future_to_file = {
                executor.submit(validate_note_file, note_file): note_file
                for note_file in note_files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                note_file = future_to_file[future]
                try:
                    file_path, error, error_type = future.result()
                    if error:
                        if error_type == "unsupported":
                            print(f"⚠️ {file_path.relative_to(validate_dir)}: {error}")
                            unsupported_files.append(file_path)
                        else:
                            print(f"❌ {file_path.relative_to(validate_dir)}: {error}")
                            corrupted_files.append(file_path)
                    else:
                        print(f"✅ {file_path.relative_to(validate_dir)}: OK")
                except Exception as e:
                    print(f"❌ {note_file.relative_to(validate_dir)}: Validation error: {e}")
                    corrupted_files.append(note_file)
        
        print(f"\n📊 Validation complete:")
        print(f"  ✅ Valid files: {len(note_files) - len(corrupted_files) - len(unsupported_files)}")
        print(f"  ❌ Corrupted files: {len(corrupted_files)}")  
        print(f"  ⚠️ Unsupported format files: {len(unsupported_files)}")
        
        if unsupported_files:
            print(f"\n⚠️ Unsupported format files (may be corrupted downloads):")
            for file_path in unsupported_files:
                print(f"  - {file_path.relative_to(validate_dir)}")
            print("💡 These files may be corrupted downloads or from newer firmware versions")
        
        if corrupted_files:
            print(f"\n🔧 Corrupted files:")
            for file_path in corrupted_files:
                print(f"  - {file_path.relative_to(validate_dir)}")
            
        # Combine all problematic files for fixing
        all_problematic_files = corrupted_files + unsupported_files
        
        if all_problematic_files and args.fix:
                # Re-download corrupted files
                if not args.ip:
                    print("\n🔍 Looking for Supernote device...")
                    ip = find_device()
                    if not ip:
                        print("\n❌ No Supernote device found for re-download.")
                        print("💡 Make sure your device is on and connected to the same network")
                        print("💡 Or use --ip to specify the device IP manually")
                        return
                else:
                    ip = args.ip
                
                # Test device connection before proceeding
                print(f"📡 Testing connection to device at {ip}...")
                device = Supernote(ip, args.port, str(validate_dir.parent))
                test_data = device.list_files("")
                if not test_data:
                    print(f"❌ Cannot connect to device at {ip}:{args.port}")
                    print("💡 Check that the device is accessible and try again")
                    return
                
                print(f"\n🔄 Re-downloading {len(all_problematic_files)} problematic files from {ip}...")
                print(f"🔍 validate_dir: {validate_dir}")  # Debug
                device = Supernote(ip, args.port, str(validate_dir.parent))
                
                success_count = 0
                fixed_files = []
                for file_path in all_problematic_files:
                    # Calculate remote path (relative to validate_dir) - just "Note/filename.note"
                    rel_path = file_path.relative_to(validate_dir)
                    remote_path = str(rel_path).replace('\\', '/')  # Ensure forward slashes
                    
                    print(f"🔄 Re-downloading {remote_path}...")
                    # Pass the full local path to preserve the supernote_files structure
                    if device.download_file(remote_path, local_path=file_path, force=True):
                        success_count += 1
                        fixed_files.append(file_path)
                        print(f"✅ Re-downloaded {remote_path}")
                    else:
                        print(f"❌ Failed to re-download {remote_path}")
                
                print(f"\n🎉 Re-download complete: {success_count}/{len(all_problematic_files)} files fixed")
                
                # Convert fixed files to PDF if requested
                if args.convert and fixed_files:
                    print(f"\n📄 Converting {len(fixed_files)} fixed files to PDF...")
                    converter = PDFConverter(vectorize=True, enable_links=True)
                    
                    convert_success = 0
                    for file_path in fixed_files:
                        print(f"🔄 Converting {file_path.name} to PDF...")
                        if converter.convert_file(file_path):
                            convert_success += 1
                        
                    print(f"🎉 Conversion complete: {convert_success}/{len(fixed_files)} PDFs created")
        elif all_problematic_files:
            print(f"\n💡 Use --fix to re-download {len(all_problematic_files)} problematic files")
        else:
            print(f"\n🎉 All files are valid!")
    
    elif args.command == "ocr":
        # Handle OCR command - works with local PDFs
        from .ocr.trocr_service import TrOCRService
        from .ocr.pdf_processor import PDFTextLayerProcessor
        from .ocr.services import ProcessPDFUseCase
        
        input_path = Path(args.input)
        
        if not input_path.exists():
            print(f"❌ Path not found: {input_path}")
            return
        
        try:
            # Handle native Supernote files differently
            if args.engine == "native":
                # Check if input is .note file(s)
                if input_path.is_file() and input_path.suffix.lower() == '.note':
                    print("🚀 Using native Supernote text extraction...")
                    from .ocr.native_service import NativeSupernoteService
                    native_service = NativeSupernoteService()
                    
                    output_path = Path(args.output) if args.output else input_path.with_stem(f"{input_path.stem}_searchable").with_suffix('.pdf')
                    
                    # Skip if searchable PDF already exists and is newer
                    if output_path.exists() and not args.force:
                        input_mtime = input_path.stat().st_mtime
                        output_mtime = output_path.stat().st_mtime
                        if output_mtime > input_mtime:
                            print(f"⏭️ Skipping {input_path.name} (searchable PDF is newer)")
                            print("💡 Use --force to re-process anyway")
                            return
                    
                    def progress_callback(current, total, message):
                        print(f"📊 [{current:3.0f}%] {message}")
                    
                    success = native_service.convert_note_to_searchable_pdf(input_path, output_path, progress_callback)
                    if success:
                        print(f"✅ Native conversion completed: {output_path}")
                    else:
                        print(f"❌ Native conversion failed")
                    return
                
                elif input_path.is_dir() or args.batch:
                    # Batch process .note files
                    print("🚀 Batch processing .note files with native extraction...")
                    from .ocr.native_service import NativeSupernoteService
                    native_service = NativeSupernoteService()
                    
                    if input_path.is_file():
                        print(f"❌ Use --batch flag to process directories")
                        return
                    
                    # Find all .note files
                    note_files = list(input_path.glob("**/*.note"))
                    if not note_files:
                        print(f"❌ No .note files found in {input_path}")
                        return
                    
                    output_dir = Path(args.output) if args.output else input_path / "searchable"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    
                    def process_single_note(note_info):
                        i, note_file, output_file = note_info
                        print(f"\n📝 Processing {i+1}/{len(note_files)}: {note_file.name}")
                        
                        def file_progress(current, total, message):
                            print(f"📊 [{current:3.0f}%] {note_file.stem}: {message}")
                        
                        try:
                            return native_service.convert_note_to_searchable_pdf(note_file, output_file, file_progress)
                        except Exception as e:
                            print(f"❌ Error processing {note_file.name}: {e}")
                            return False
                    
                    # Prepare work items
                    work_items = []
                    skipped_count = 0
                    for i, note_file in enumerate(note_files):
                        output_file = output_dir / f"{note_file.stem}_searchable.pdf"
                        
                        # Skip if searchable PDF already exists and is newer
                        if output_file.exists() and not args.force:
                            input_mtime = note_file.stat().st_mtime
                            output_mtime = output_file.stat().st_mtime
                            if output_mtime > input_mtime:
                                print(f"⏭️ Skipping {note_file.name} (searchable PDF is newer)")
                                skipped_count += 1
                                continue
                        
                        work_items.append((i, note_file, output_file))
                    
                    # Process in parallel
                    successful = 0
                    with ThreadPoolExecutor(max_workers=args.workers) as executor:
                        # Submit all tasks
                        future_to_item = {
                            executor.submit(process_single_note, item): item
                            for item in work_items
                        }
                        
                        # Collect results as they complete
                        for future in as_completed(future_to_item):
                            if future.result():
                                successful += 1
                    
                    print(f"\n🎉 Native batch conversion completed: {successful}/{len(note_files)} files")
                    if skipped_count > 0:
                        print(f"⏭️ Skipped {skipped_count} files (searchable PDFs already exist)")
                        print(f"💡 Use --force to re-process existing files")
                    return
                
                else:
                    print(f"❌ Native engine requires .note files, got: {input_path.suffix}")
                    print(f"💡 Use --engine llava or --engine trocr for PDF files")
                    return
            
            # Initialize OCR services for PDF processing
            if args.engine == "llava":
                print("🚀 Initializing LLaVA OCR service...")
                from .ocr.llava_service import LLaVAOCRService
                ocr_service = LLaVAOCRService(base_url=args.ollama_url)
            else:
                print("🚀 Initializing TrOCR service...")
                ocr_service = TrOCRService()
            
            pdf_processor = PDFTextLayerProcessor()
            use_case = ProcessPDFUseCase(ocr_service, pdf_processor)
            
            def progress_callback(current, total, message):
                if total > 0:
                    percent = (current / total) * 100
                    print(f"📊 [{percent:5.1f}%] {message}")
                else:
                    print(f"📊 {message}")
            
            if input_path.is_file() and input_path.suffix.lower() == '.pdf':
                # Process single PDF file
                output_path = Path(args.output) if args.output else input_path.with_stem(f"{input_path.stem}_searchable")
                
                # Check if PDF already has searchable text
                if not args.force and pdf_processor.has_searchable_text(input_path):
                    print(f"⏭️ Skipping {input_path.name} (already has searchable text)")
                    print("💡 Use --force to process anyway")
                    return
                
                print(f"🔍 Processing {input_path.name} -> {output_path.name}")
                processed_pages = use_case.process_pdf(input_path, output_path, progress_callback)
                
                total_text_blocks = sum(len(page.ocr_result.text_blocks) for page in processed_pages if page.has_text)
                print(f"✅ OCR completed: {total_text_blocks} text blocks across {len(processed_pages)} pages")
                
                # Print recognized text for review
                print(f"\n📝 Recognized Text:")
                print("=" * 50)
                for page in processed_pages:
                    if page.has_text:
                        print(f"\n--- Page {page.page_number + 1} ---")
                        for i, block in enumerate(page.ocr_result.text_blocks):
                            confidence_indicator = "🟢" if block.confidence > 0.7 else "🟡" if block.confidence > 0.5 else "🔴"
                            print(f"{confidence_indicator} Block {i+1} (conf: {block.confidence:.2f}): {block.text}")
                print("=" * 50)
                
            elif input_path.is_dir() or args.batch:
                # Process directory of PDFs
                if input_path.is_file():
                    print(f"❌ Use --batch flag to process directories")
                    return
                
                output_dir = Path(args.output) if args.output else input_path / "searchable"
                
                print(f"📁 Batch processing PDFs in {input_path}")
                successful, total = use_case.process_batch(input_path, output_dir, args.workers, progress_callback)
                print(f"🎉 Batch OCR completed: {successful}/{total} files processed successfully")
                
            else:
                print(f"❌ Invalid input: {input_path}")
                print("💡 Provide a PDF file or directory with --batch flag")
                
        except ImportError as e:
            print(f"❌ Missing dependencies: {e}")
            print("💡 Install with: uv add transformers torch")
        except Exception as e:
            print(f"❌ OCR processing failed: {e}")
            import traceback
            traceback.print_exc()
    
    elif args.command == "merge":
        # Handle merge command - works with local files
        from .merger import DateBasedMerger, MergeConfig
        
        directory = Path(args.directory)
        
        if not directory.exists():
            print(f"❌ Directory not found: {directory}")
            return
        
        # Create merger with user configuration
        config = MergeConfig(
            pdf_output_dir=args.pdf_output,
            markdown_output_dir=args.markdown_output,
            time_range=args.time_range
        )
        
        merger = DateBasedMerger(config)
        
        # Execute based on user flags
        if args.pdf_only:
            merger.merge_pdfs_by_date(directory)
        elif args.markdown_only:
            merger.merge_markdown_by_date(directory)
        else:
            # Default: merge both
            merger.merge_all_by_date(directory)


if __name__ == "__main__":
    main()