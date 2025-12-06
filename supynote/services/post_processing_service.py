"""Shared post-processing service for OCR and merging operations."""
import os
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class PostProcessingService:
    """Handles OCR and merging operations after download/conversion."""
    
    def process_downloaded_files(
        self,
        local_dir: Path,
        device,
        args,
        conversion_workers: int = 8,
        output_dir: Optional[Path] = None
    ) -> None:
        """Process downloaded files with OCR and merger."""
        
        # OCR the converted PDFs if requested (do this BEFORE merging)
        if getattr(args, 'ocr', False):
            self._process_ocr(local_dir, args, conversion_workers)
        
        # Merge searchable PDFs by date if requested (do this AFTER OCR)
        if getattr(args, 'merge_by_date', False):
            self._process_merger(local_dir, device, args, output_dir)
    
    def _process_ocr(self, local_dir: Path, args, conversion_workers: int) -> None:
        """Handle OCR processing."""
        print("🔍 Starting OCR processing...")
        from ..ocr.native_service import NativeSupernoteService
        from ..converter import PDFConverter
        
        native_service = NativeSupernoteService()
        
        # Find all .note files that were converted
        all_note_files = list(local_dir.glob("**/*.note"))
        
        # Filter by time range if specified
        if getattr(args, 'time_range', 'all') != "all":
            temp_converter = PDFConverter()
            note_files = [f for f in all_note_files if temp_converter._should_include_file(f, args.time_range)]
            if len(note_files) < len(all_note_files):
                print(f"🔍 Creating searchable PDFs for {len(note_files)} files (filtered from {len(all_note_files)} by time range)...")
            else:
                print(f"🔍 Creating searchable PDFs for {len(note_files)} files...")
        else:
            note_files = all_note_files
            print(f"🔍 Creating searchable PDFs for {len(note_files)} files...")
        
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
        with ThreadPoolExecutor(max_workers=conversion_workers) as executor:
            futures = {executor.submit(process_note_for_ocr, note_file): note_file 
                      for note_file in note_files}
            
            for future in as_completed(futures):
                if future.result():
                    successful_ocr += 1
        
        print(f"🎉 Created {successful_ocr}/{len(note_files)} searchable PDFs")
        
        # Display warning summary
        warning_summary = native_service.get_warning_summary()
        if warning_summary:
            print(f"\n⚠️ Text recognition warnings found in {len(warning_summary)} document(s):")
            for doc_path, warnings in sorted(warning_summary.items()):
                filename = Path(doc_path).name
                print(f"  📄 {filename}: {len(warnings)} page(s) with incomplete recognition")
            
            # Save report if requested
            report_path = local_dir / "ocr_warnings_report.txt"
            native_service.save_warning_report(report_path)
            print(f"  📝 Full report saved to: {report_path}")
    
    def _process_merger(self, local_dir: Path, device, args, output_dir: Optional[Path] = None) -> None:
        """Handle merger processing."""
        print("🚀 Starting merger processing...")
        from ..merger import DateBasedMerger, MergeConfig
        
        # Use output_dir if provided, otherwise use device's processed dir (cache location)
        if output_dir:
            pdf_output = str(output_dir / "pdfs")
            markdown_output = str(output_dir / "markdowns")
        else:
            pdf_output = str(device.processed_dir / "pdfs")
            markdown_output = str(device.processed_dir / "markdowns")
        
        # Get journals directory from env var or args, with fallback to None
        journals_dir_str = os.environ.get("SUPYNOTE_JOURNALS_DIR") or getattr(args, 'journals_dir', None)
        journals_dir = Path(journals_dir_str) if journals_dir_str else None

        merge_config = MergeConfig(
            pdf_output_dir=pdf_output,
            markdown_output_dir=markdown_output,
            time_range=getattr(args, 'time_range', 'all'),
            journals_dir=journals_dir
        )
        merger = DateBasedMerger(merge_config)
        merger.merge_all_by_date(local_dir)