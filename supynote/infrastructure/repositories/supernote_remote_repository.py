"""Implementation of RemoteNoteRepository using Supernote device API."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import hashlib

from ...domain.note_management.repositories.note_repository import RemoteNoteRepository
from ...domain.note_management.entities.note import Note
from ...domain.note_management.value_objects.note_path import NotePath
from ...domain.note_management.value_objects.note_id import NoteId
from ...supernote import Supernote


class SupernoteRemoteRepository(RemoteNoteRepository):
    """Remote repository implementation using Supernote device."""
    
    def __init__(self, device: Supernote):
        self._device = device
    
    def list_remote_notes(self, directory: str = "") -> List[Note]:
        """List notes available on the remote device."""
        data = self._device.list_files(directory)
        if not data or "fileList" not in data:
            return []
        
        notes = []
        for item in data["fileList"]:
            if not item["isDirectory"]:
                # Create Note entity from remote file info
                note_path = NotePath(item["uri"])
                
                # Parse dates from item info
                created_at = self._parse_date(item.get("date"))
                # Try multiple possible field names for modification time
                modified_at = self._parse_modified_date(item)
                
                # Get file size
                size = item.get("size", 0)
                
                # Generate a simple checksum from basic file info
                checksum = self._generate_checksum(item)
                
                note = Note.create_from_remote(
                    path=note_path,
                    created_at=created_at,
                    modified_at=modified_at,
                    size=size,
                    checksum=checksum
                )
                notes.append(note)
            else:
                # Recursively process subdirectories
                subdirectory_path = item["uri"]
                sub_notes = self.list_remote_notes(subdirectory_path)
                notes.extend(sub_notes)
        
        return notes
    
    def download_note(self, remote_path: NotePath, local_path: NotePath) -> bool:
        """Download a note from the remote device."""
        local_file_path = Path(local_path.full_path)
        return self._device.download_file(
            remote_path.full_path,
            local_path=local_file_path,
            force=False,
            check_size=True
        )
    
    def download_note_forced(self, remote_path: NotePath, local_path: NotePath) -> bool:
        """Download a note from the remote device, forcing redownload."""
        local_file_path = Path(local_path.full_path)
        return self._device.download_file(
            remote_path.full_path,
            local_path=local_file_path,
            force=True,
            check_size=False
        )
    
    def get_remote_checksum(self, path: NotePath) -> Optional[str]:
        """Get the checksum of a remote note."""
        # For now, we'll use the file metadata as a simple checksum
        # In a more robust implementation, we might download a small portion
        # of the file or use device-provided checksums
        directory = str(Path(path.full_path).parent)
        filename = Path(path.full_path).name
        
        data = self._device.list_files(directory)
        if not data or "fileList" not in data:
            return None
        
        for item in data["fileList"]:
            if item.get("name") == filename:
                return self._generate_checksum(item)
        
        return None
    
    async def download_notes_async(
        self,
        notes_to_download: List[tuple[Note, NotePath]],  # (note, local_path) pairs
        max_workers: int = 20,
        progress_callback: Optional[callable] = None
    ) -> tuple[int, int]:
        """
        Download multiple notes asynchronously.
        
        Returns (successful_downloads, total_downloads).
        """
        if not hasattr(self._device, 'download_directory_async'):
            # Fallback to sync download
            return await self._download_notes_sync_fallback(notes_to_download, max_workers, progress_callback)
        
        # Group downloads by directory for efficiency
        downloads_by_dir = {}
        for note, local_path in notes_to_download:
            directory = str(Path(note.path.full_path).parent)
            if directory not in downloads_by_dir:
                downloads_by_dir[directory] = []
            downloads_by_dir[directory].append((note, local_path))
        
        total_downloads = len(notes_to_download)
        successful_downloads = 0
        current_download = 0
        
        # Process each directory
        for directory, dir_downloads in downloads_by_dir.items():
            if progress_callback:
                progress_callback(current_download, total_downloads, f"Processing directory: {directory}")
            
            # For async downloads, we'll use the device's async capabilities
            # This is a simplified version - in practice, you might want to handle each file individually
            try:
                success, total = await self._device.download_directory_async(
                    directory, max_workers, force=False, check_size=True
                )
                successful_downloads += success
            except Exception as e:
                print(f"❌ Error downloading directory {directory}: {e}")
            
            current_download += len(dir_downloads)
        
        return successful_downloads, total_downloads
    
    async def _download_notes_sync_fallback(
        self,
        notes_to_download: List[tuple[Note, NotePath]],
        max_workers: int,
        progress_callback: Optional[callable] = None
    ) -> tuple[int, int]:
        """Fallback sync download implementation."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        successful_downloads = 0
        total_downloads = len(notes_to_download)
        
        def download_single(note_and_path):
            note, local_path = note_and_path
            return self.download_note(note.path, local_path)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(download_single, note_and_path): note_and_path
                for note_and_path in notes_to_download
            }
            
            for i, future in enumerate(as_completed(futures)):
                try:
                    if future.result():
                        successful_downloads += 1
                    
                    if progress_callback:
                        note, _ = futures[future]
                        progress_callback(i + 1, total_downloads, f"Downloaded: {note.path.filename}")
                
                except Exception as e:
                    note, _ = futures[future]
                    print(f"❌ Error downloading {note.path.full_path}: {e}")
        
        return successful_downloads, total_downloads
    
    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse date string from device response."""
        if not date_str:
            return datetime.now()

        try:
            # Try different date formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(date_str.split()[0] if ' ' in date_str else date_str, fmt.split()[0])
                except ValueError:
                    continue

            # If all formats fail, return current time
            return datetime.now()
        except Exception:
            return datetime.now()

    def _parse_modified_date(self, item: Dict[str, Any]) -> datetime:
        """Parse modification date from device metadata, trying multiple field names."""
        # Try common modification time field names in order of preference
        for field_name in ["mtime", "modifiedTime", "lastModified", "modified", "date"]:
            if field_name in item and item[field_name]:
                return self._parse_date(item[field_name])

        # Fallback to creation date if no modification time found
        return self._parse_date(item.get("date"))

    def _generate_checksum(self, item: Dict[str, Any]) -> str:
        """Generate a simple checksum from file metadata."""
        # Create a hash based on file name, size, and date
        content = f"{item.get('name', '')}{item.get('size', 0)}{item.get('date', '')}"
        return hashlib.md5(content.encode()).hexdigest()[:16]