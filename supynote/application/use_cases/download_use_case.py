"""Use case for download and related operations."""
from typing import Optional, Any, Dict
from pathlib import Path
import asyncio

from ...infrastructure.network.network_discovery_service import NetworkDiscoveryService
from ...domain.device_management.repositories.device_repository import DeviceRepository


class DownloadUseCase:
    """Handles download and related operations."""
    
    def __init__(
        self,
        device_repository: DeviceRepository,
        discovery_service: NetworkDiscoveryService
    ):
        """Initialize the adapter."""
        self._device_repository = device_repository
        self._discovery_service = discovery_service
    
    def execute_download(self, args: Any) -> bool:
        """Execute download command using legacy code."""
        ip = self._get_device_ip(args)
        if not ip:
            print("❌ No Supernote device found. Use --ip to specify manually.")
            return False
        
        from ...supernote import Supernote
        from ...converter import PDFConverter
        
        device = Supernote(ip, args.port, args.output)
        
        if args.use_async:
            # Use high-performance async downloader
            async def async_download():
                try:
                    if "/" in args.path and not args.path.endswith("/"):
                        # Downloading a specific file
                        success = device.download_file(args.path, force=args.force, check_size=args.check_size)
                        if success and args.convert_pdf and args.path.lower().endswith('.note'):
                            local_file = device.local_root / args.path.lstrip('/')
                            converter = PDFConverter(vectorize=True, enable_links=True)
                            converter.convert_file(local_file)
                    else:
                        # Downloading a directory with async
                        success, total = await device.download_directory_async(
                            args.path, args.workers, args.force, args.check_size, 
                            time_range=args.time_range)
                        print(f"🎉 Async download completed: {success}/{total} files")
                        
                        if args.convert_pdf:
                            # Convert downloaded files
                            converter = PDFConverter(vectorize=True, enable_links=True, verbose=getattr(args, 'verbose', False))
                            local_dir = device.raw_dir / args.path.lstrip('/')
                            if local_dir.exists():
                                converter.convert_directory(local_dir, max_workers=args.conversion_workers, time_range=args.time_range)
                                
                                # Handle OCR and merger processing
                                from ...services.post_processing_service import PostProcessingService
                                post_processor = PostProcessingService()
                                
                                # Use processed_output if provided
                                output_dir = Path(args.processed_output) if getattr(args, 'processed_output', None) else None
                                post_processor.process_downloaded_files(local_dir, device, args, args.conversion_workers, output_dir)
                except Exception as e:
                    print(f"❌ Download failed: {e}")
                    return False
                finally:
                    # Clean up async session
                    await device.close_async()
                return True
            
            return asyncio.run(async_download())
        else:
            # Sync download
            if "/" in args.path and not args.path.endswith("/"):
                return device.download_file(args.path, force=args.force)
            else:
                success, total = device.download_directory(args.path, args.workers, args.force)
                print(f"Downloaded {success}/{total} files")
                return success > 0
    
    def execute_convert(self, args: Any) -> bool:
        """Execute convert command using legacy code."""
        from ...converter import PDFConverter
        
        input_path = Path(args.path)
        if not input_path.exists():
            print(f"❌ Path does not exist: {input_path}")
            return False
        
        converter = PDFConverter(
            vectorize=not args.no_vector,
            enable_links=not args.no_links
        )
        
        if input_path.is_file():
            output_dir = Path(args.output) if args.output else None
            converter.convert_file(input_path, output_dir)
        elif input_path.is_dir():
            output_dir = Path(args.output) if args.output else None
            converter.convert_directory(input_path, output_dir, recursive=args.recursive, max_workers=args.workers)
        else:
            print(f"❌ Invalid path: {input_path}")
            return False
        
        return True
    
    def execute_validate(self, args: Any) -> bool:
        """Execute validate command using legacy code."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from ...converter import PDFConverter
        
        directory = Path(args.directory)
        if not directory.exists():
            print(f"❌ Directory does not exist: {directory}")
            return False
        
        # Find all .note files
        note_files = list(directory.rglob("*.note"))
        print(f"🔍 Found {len(note_files)} .note files to validate")
        
        converter = PDFConverter()
        problematic_files = []
        
        def validate_file(file_path):
            try:
                # Try to convert to validate
                converter.convert_file(file_path, Path("/tmp"))
                return file_path, True, None
            except Exception as e:
                return file_path, False, str(e)
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(validate_file, f): f for f in note_files}
            
            for future in as_completed(futures):
                file_path, success, error = future.result()
                if not success:
                    problematic_files.append((file_path, error))
                    print(f"❌ {file_path}: {error}")
        
        if problematic_files:
            print(f"\n⚠️ Found {len(problematic_files)} problematic files")
            
            if args.fix:
                ip = self._get_device_ip(args)
                if ip:
                    print("🔧 Re-downloading problematic files...")
                    from ...supernote import Supernote
                    device = Supernote(ip, args.port)
                    
                    for file_path, _ in problematic_files:
                        relative_path = file_path.relative_to(directory)
                        device.download_file(str(relative_path), force=True)
                        
                        if args.convert:
                            converter.convert_file(file_path)
        else:
            print("✅ All files validated successfully")
        
        return True
    
    def execute_ocr(self, args: Any) -> bool:
        """Execute OCR command using legacy code."""
        input_path = Path(args.input)

        if not input_path.exists():
            print(f"❌ Path does not exist: {input_path}")
            return False

        if args.engine == "native":
            from ...ocr.native_service import NativeSupernoteService
            service = NativeSupernoteService()

            if args.batch and input_path.is_dir():
                # Batch process directory
                note_files = list(input_path.glob("*.note"))
                print(f"🔍 Found {len(note_files)} .note files to process")

                for note_file in note_files:
                    output_file = note_file.with_suffix('.pdf')
                    if args.output:
                        output_dir = Path(args.output)
                        output_dir.mkdir(exist_ok=True)
                        output_file = output_dir / output_file.name

                    print(f"🔍 Processing {note_file.name}...")
                    service.convert_note_to_searchable_pdf(note_file, output_file)
            else:
                # Single file
                output_file = Path(args.output) if args.output else input_path.with_suffix('.pdf')
                service.convert_note_to_searchable_pdf(input_path, output_file)
        else:
            print(f"❌ OCR engine '{args.engine}' not yet implemented in DDD")
            return False

        return True

    def execute_merge(self, args: Any) -> bool:
        """Execute merge command using DateBasedMerger."""
        from ...merger import DateBasedMerger, MergeConfig
        import os

        directory = Path(args.directory)
        if not directory.exists():
            print(f"❌ Directory does not exist: {directory}")
            return False

        # Get journals directory from env var or args
        journals_dir_str = os.environ.get("SUPYNOTE_JOURNALS_DIR") or getattr(args, 'journals_dir', None)
        journals_dir = Path(journals_dir_str) if journals_dir_str else None

        # Get assets directory from env var if set
        assets_dir_str = os.environ.get("SUPYNOTE_ASSETS_DIR")
        assets_dir = Path(assets_dir_str) if assets_dir_str else None

        merge_config = MergeConfig(
            pdf_output_dir=args.pdf_output,
            markdown_output_dir=args.markdown_output,
            time_range=args.time_range,
            journals_dir=journals_dir,
            assets_dir=assets_dir
        )

        merger = DateBasedMerger(merge_config)

        if args.pdf_only:
            merger.merge_pdfs_by_date(directory)
        elif args.markdown_only:
            merger.merge_markdown_by_date(directory)
        else:
            merger.merge_all_by_date(directory)

        return True
    
    def _get_device_ip(self, args: Any) -> Optional[str]:
        """Get device IP from args or discovery."""
        if hasattr(args, 'ip') and args.ip:
            return args.ip
        
        # Try discovery
        ip = self._discovery_service.discover_device()
        if ip:
            from ...domain.device_management.entities.device import Device
            device = Device.discover(ip, "8089")
            self._device_repository.save(device)
        
        return ip