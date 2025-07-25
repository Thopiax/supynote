#!/usr/bin/env python3

import argparse
import webbrowser
from pathlib import Path

from .device_finder import find_device
from .supernote import Supernote
from .converter import PDFConverter


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
    download_parser = subparsers.add_parser("download", help="Download files from device")
    download_parser.add_argument("path", help="File or directory path to download")
    download_parser.add_argument("--workers", type=int, default=20, help="Number of concurrent downloads (default: 20)")
    download_parser.add_argument("--async", dest="use_async", action="store_true", default=True, help="Use high-performance async downloader")
    download_parser.add_argument("--no-async", dest="use_async", action="store_false", help="Use traditional sync downloader")
    download_parser.add_argument("--convert-pdf", action="store_true", help="Convert downloaded .note files to PDF")
    download_parser.add_argument("--conversion-workers", type=int, default=4, help="Number of parallel PDF conversion workers (default: 4)")
    download_parser.add_argument("--force", action="store_true", help="Force re-download even if files exist locally")
    download_parser.add_argument("--check-size", action="store_true", default=True, help="Skip files if local size matches remote (default: true)")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert .note files to PDF")
    convert_parser.add_argument("path", help="File or directory path to convert")
    convert_parser.add_argument("--output", "-o", help="Output directory or file path")
    convert_parser.add_argument("--no-vector", action="store_true", help="Disable vector format (use raster)")
    convert_parser.add_argument("--no-links", action="store_true", help="Disable hyperlinks in PDF")
    convert_parser.add_argument("--recursive", "-r", action="store_true", default=True, help="Process subdirectories (default: true)")
    convert_parser.add_argument("--workers", type=int, default=4, help="Number of parallel conversion workers (default: 4)")
    
    # Info command
    subparsers.add_parser("info", help="Show device information")
    
    # OCR command
    ocr_parser = subparsers.add_parser("ocr", help="OCR handwritten PDFs to make them searchable")
    ocr_parser.add_argument("input", help="PDF file or directory to process")
    ocr_parser.add_argument("--output", "-o", help="Output file or directory")
    ocr_parser.add_argument("--batch", action="store_true", help="Process directory of PDFs")
    ocr_parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers for batch processing (default: 4)")
    ocr_parser.add_argument("--check-existing", action="store_true", default=True, help="Skip PDFs that already have searchable text")
    ocr_parser.add_argument("--force", action="store_true", help="Process even if PDF already has searchable text")
    ocr_parser.add_argument("--engine", choices=["native", "llava", "trocr"], default="native", help="OCR engine to use (default: native)")
    ocr_parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama API URL (default: http://localhost:11434)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Handle commands that don't need device connection
    if args.command == "find":
        ip = find_device()
        if ip and args.open:
            url = f"http://{ip}:{args.port}"
            print(f"🌐 Opening {url} in browser...")
            webbrowser.open(url)
        return
    
    elif args.command in ["convert", "ocr"]:
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
                    else:
                        # Downloading a directory with async
                        success, total = await device.download_directory_async(args.path, args.workers, args.force, args.check_size)
                        print(f"🎉 Async download completed: {success}/{total} files")
                        if args.convert_pdf:
                            local_dir = device.local_root / args.path.lstrip('/')
                            converter = PDFConverter(vectorize=True, enable_links=True)
                            converter.convert_directory(local_dir, max_workers=args.conversion_workers)
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
            else:
                # Downloading a directory
                success, total = device.download_directory(args.path, args.workers, args.force, args.check_size)
                print(f"📊 Sync download completed: {success}/{total} files")
                if args.convert_pdf:
                    local_dir = device.local_root / args.path.lstrip('/')
                    converter = PDFConverter(vectorize=True, enable_links=True)
                    converter.convert_directory(local_dir, max_workers=args.conversion_workers)
    
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
        info = device.get_device_info()
        print(f"\n📱 Supernote Device Info:")
        print(f"  IP: {info['ip']}")
        print(f"  Port: {info['port']}")
        print(f"  URL: {info['url']}")
        print(f"  Status: {info['status']}")
        if args.output:
            print(f"  Local directory: {Path(args.output).absolute()}")
    
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
                    for i, note_file in enumerate(note_files):
                        output_file = output_dir / f"{note_file.stem}_searchable.pdf"
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


if __name__ == "__main__":
    main()