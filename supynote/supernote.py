import asyncio
import json
import os
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from .converter import PDFConverter

try:
    import aiohttp
    import aiofiles
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False


class Supernote:
    """Simple interface to interact with Supernote devices."""
    
    def __init__(self, ip_address: str, port: str = "8089", local_root: Optional[str] = None, verbose: bool = False):
        self.ip_address = ip_address
        self.port = port
        self.remote_root = f"http://{ip_address}:{port}"
        self.local_root = Path(local_root) if local_root else Path.cwd() / "data"
        self.verbose = verbose
        
        # Create directory structure
        # Cache for intermediate .note files (temp storage)
        self.cache_dir = Path.home() / ".cache" / "supynote"
        # User-facing output directories
        self.pdfs_dir = self.local_root / "pdfs"    # PDF outputs
        self.markdowns_dir = self.local_root / "markdowns"  # Markdown outputs

        # Ensure directories exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
        self.markdowns_dir.mkdir(parents=True, exist_ok=True)
        
        # Async session (created when needed)
        self._session: Optional['aiohttp.ClientSession'] = None
    
    def _should_include_file(self, file_info: Dict, time_range: str) -> bool:
        """Check if file should be included based on time range filter using modification time."""
        if time_range == "all":
            return True

        # Try to get modification time from multiple possible field names
        file_date_str = None
        for field_name in ["mtime", "modifiedTime", "lastModified", "modified", "date"]:
            if field_name in file_info and file_info[field_name]:
                file_date_str = file_info[field_name]
                break

        if not file_date_str:
            # If no date info, include the file by default
            return True

        try:
            # Parse the date string (format might vary, adjust as needed)
            # Assuming format like "2024-01-15 10:30" or similar
            file_date = datetime.strptime(file_date_str.split()[0], "%Y-%m-%d")
            now = datetime.now()

            # Calculate the cutoff date based on time range
            if time_range == "week":
                cutoff = now - timedelta(days=7)
            elif time_range == "2weeks":
                cutoff = now - timedelta(days=14)
            elif time_range == "month":
                cutoff = now - timedelta(days=30)
            else:
                return True  # Unknown range, include by default

            return file_date >= cutoff

        except (ValueError, IndexError) as e:
            # If we can't parse the date, include the file by default
            print(f"⚠️ Could not parse date '{file_date_str}': {e}")
            return True
    
    def _get_headers(self, force_no_cache: bool = False):
        """Get Safari-like headers for compatibility."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Priority': 'u=0, i',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if force_no_cache:
            headers.update({
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            })
            
        return headers
    
    def list_files(self, directory: str = "") -> Optional[Dict]:
        """List files and directories on the Supernote device."""
        url = f"{self.remote_root}/{directory}" if directory else self.remote_root
        
        try:
            print(f"📂 Listing files at {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            script_tag = soup.find("script", string=lambda text: text and "const json" in text)
            
            if script_tag:
                json_data = script_tag.string.split("const json = ")[1].strip().split("'")[1]
                data = json.loads(json_data)
                return data
                
        except requests.RequestException as e:
            print(f"❌ Error connecting to device: {e}")
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            
        return None
    
    def _should_skip_file(self, remote_file_info: Dict, local_path: Path, force: bool = False, check_size: bool = True) -> bool:
        """Check if file should be skipped based on existence and size."""
        if force:
            return False
            
        if not local_path.exists():
            return False
            
        if not check_size:
            if self.verbose:
                print(f"⏭️ Skipping {local_path.name} (exists locally)")
            return True
            
        # Compare file sizes if available
        if "size" in remote_file_info:
            local_size = local_path.stat().st_size
            remote_size = remote_file_info["size"]
            
            if local_size == remote_size:
                if self.verbose:
                    print(f"⏭️ Skipping {local_path.name} (same size: {local_size} bytes)")
                return True
            else:
                print(f"🔄 Re-downloading {local_path.name} (size changed: {local_size} → {remote_size} bytes)")
                return False
        else:
            # No size info available, skip if file exists
            if self.verbose:
                print(f"⏭️ Skipping {local_path.name} (exists locally)")
            return True

    def download_file(self, remote_path: str, local_path: Optional[Path] = None, force: bool = False, check_size: bool = True, remote_file_info: Optional[Dict] = None) -> bool:
        """Download a single file from the device with skip logic."""
        if not local_path:
            local_path = self.cache_dir / remote_path.lstrip('/')
        
        # Check if we should skip this file
        if remote_file_info and self._should_skip_file(remote_file_info, local_path, force, check_size):
            return True  # Consider skipped files as "successful"
        
        # Ensure parent directory exists  
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        url = f"{self.remote_root}/{remote_path.lstrip('/')}"
        
        try:
            print(f"⬇️ Downloading {remote_path}")
            print(f"🔗 URL: {url}")
            
            # Use no-cache headers when force=True to ensure fresh download
            response = requests.get(url, headers=self._get_headers(force_no_cache=force), timeout=30)
            response.raise_for_status()
            
            # Get content size and type for debugging
            content_size = len(response.content)
            content_type = response.headers.get('content-type', 'unknown')
            print(f"📊 Downloaded {content_size} bytes, Content-Type: {content_type}")
            
            # Check if we got HTML instead of binary content
            if content_type.lower().startswith('text/html') or response.content.startswith(b'<!DOCTYPE') or response.content.startswith(b'<html'):
                print(f"⚠️ Warning: Got HTML content instead of binary file!")
                print(f"🔍 First 200 chars: {response.content[:200]}")
                return False
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Downloaded to {local_path}")
            return True
            
        except requests.RequestException as e:
            print(f"❌ Error downloading {remote_path}: {e}")
            return False
    
    def download_directory(self, directory: str = "", max_workers: int = 4, force: bool = False, check_size: bool = True, time_range: str = "all") -> tuple[int, int]:
        """Download all files from a directory (recursive) with skip logic and time filtering."""
        data = self.list_files(directory)
        if not data or "fileList" not in data:
            print(f"❌ No files found in {directory}")
            return 0, 0
        
        files_to_download = []
        file_info_map = {}
        directories_to_process = []
        skipped_by_time = 0
        
        for item in data["fileList"]:
            if item["isDirectory"]:
                directories_to_process.append(item["uri"])
            else:
                # Apply time range filter
                if self._should_include_file(item, time_range):
                    file_path = item["uri"]
                    files_to_download.append(file_path)
                    file_info_map[file_path] = item
                else:
                    skipped_by_time += 1
        
        successful_downloads = 0
        total_files = len(files_to_download)
        
        # Download files in parallel
        if files_to_download:
            print(f"📦 Processing {total_files} files from {directory}")
            if skipped_by_time > 0 and self.verbose:
                print(f"⏭️ Skipping {skipped_by_time} files outside time range: {time_range}")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        self.download_file, 
                        file_path, 
                        None,  # local_path 
                        force, 
                        check_size, 
                        file_info_map.get(file_path)
                    ) 
                    for file_path in files_to_download
                ]
                for future in as_completed(futures):
                    if future.result():
                        successful_downloads += 1
            
            print(f"📊 Processed {successful_downloads}/{total_files} files successfully")
        
        # Process subdirectories recursively
        for subdir in directories_to_process:
            subdir_success, subdir_total = self.download_directory(subdir.lstrip('/'), max_workers, force, check_size, time_range)
            successful_downloads += subdir_success
            total_files += subdir_total
        
        return successful_downloads, total_files
    
    async def download_directory_async(self, directory: str = "", max_concurrent: int = 20, force: bool = False, check_size: bool = True, time_range: str = "all") -> tuple[int, int]:
        """
        High-performance async directory download with connection pooling and time filtering.
        
        Args:
            directory: Directory to download
            max_concurrent: Maximum concurrent downloads (default: 20)
            force: Force re-download even if files exist
            check_size: Skip files if local size matches remote
            time_range: Time range filter (week, 2weeks, month, all)
            
        Returns:
            Tuple of (successful_downloads, total_files)
        """
        if not ASYNC_AVAILABLE:
            print("❌ Async dependencies not available. Run: uv add aiohttp aiofiles")
            return 0, 0
        
        # Ensure we have an async session
        if not self._session or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=max_concurrent * 2,
                limit_per_host=max_concurrent * 2,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )
            
            timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
            
            self._session = aiohttp.ClientSession(
                headers=self._get_headers(),
                connector=connector,
                timeout=timeout,
                trust_env=True,
            )
        
        try:
            # Get directory listing
            data = await self._list_files_async(directory)
            if not data or "fileList" not in data:
                print(f"❌ No files found in {directory}")
                return 0, 0
            
            # Separate files and directories
            files_to_download = []
            file_info_map = {}
            directories_to_process = []
            skipped_by_time = 0
            
            for item in data["fileList"]:
                if item["isDirectory"]:
                    directories_to_process.append(item["uri"])
                else:
                    # Apply time range filter
                    if self._should_include_file(item, time_range):
                        file_path = item["uri"]
                        files_to_download.append(file_path)
                        file_info_map[file_path] = item
                    else:
                        skipped_by_time += 1
            
            successful_downloads = 0
            total_files = len(files_to_download)
            
            # Download files with controlled concurrency
            if files_to_download:
                print(f"📦 Processing {total_files} files from {directory} (max {max_concurrent} concurrent)")
                if skipped_by_time > 0 and self.verbose:
                    print(f"⏭️ Skipping {skipped_by_time} files outside time range: {time_range}")
                
                # Semaphore to limit concurrent downloads
                semaphore = asyncio.Semaphore(max_concurrent)
                
                # Create download tasks
                tasks = [
                    self._download_file_async(file_path, semaphore=semaphore, force=force, check_size=check_size, remote_file_info=file_info_map.get(file_path))
                    for file_path in files_to_download
                ]
                
                # Execute all downloads concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successful downloads
                successful_downloads = sum(1 for result in results if result is True)
                
                print(f"📊 Processed {successful_downloads}/{total_files} files successfully")
            
            # Process subdirectories recursively
            for subdir in directories_to_process:
                subdir_success, subdir_total = await self.download_directory_async(subdir.lstrip('/'), max_concurrent, force, check_size, time_range)
                successful_downloads += subdir_success
                total_files += subdir_total
            
            return successful_downloads, total_files
            
        finally:
            # Keep session open for potential reuse, but user should call close_async() when done
            pass
    
    async def _list_files_async(self, directory: str = "") -> Optional[Dict]:
        """Async version of list_files."""
        url = f"{self.remote_root}/{directory}" if directory else self.remote_root
        
        try:
            async with self._session.get(url) as response:
                response.raise_for_status()
                html_content = await response.text()
                
                soup = BeautifulSoup(html_content, "html.parser")
                script_tag = soup.find("script", string=lambda text: text and "const json" in text)
                
                if script_tag:
                    json_data = script_tag.string.split("const json = ")[1].strip().split("'")[1]
                    data = json.loads(json_data)
                    return data
                    
        except aiohttp.ClientError as e:
            print(f"❌ Error connecting to device: {e}")
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            
        return None
    
    async def _download_file_async(self, remote_path: str, local_path: Optional[Path] = None, semaphore: Optional[asyncio.Semaphore] = None, force: bool = False, check_size: bool = True, remote_file_info: Optional[Dict] = None) -> bool:
        """Async version of download_file with semaphore support."""
        if not local_path:
            local_path = self.cache_dir / remote_path.lstrip('/')
        
        # Check if we should skip this file
        if remote_file_info and self._should_skip_file(remote_file_info, local_path, force, check_size):
            return True  # Consider skipped files as "successful"
        
        # Ensure parent directory exists  
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        url = f"{self.remote_root}/{remote_path.lstrip('/')}"
        
        async def _download():
            try:
                print(f"⬇️ Downloading {remote_path}")
                async with self._session.get(url) as response:
                    response.raise_for_status()
                    
                    # Stream the file to disk for memory efficiency
                    async with aiofiles.open(local_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):  # 8KB chunks
                            await f.write(chunk)
                
                print(f"✅ Downloaded to {local_path}")
                return True
                
            except aiohttp.ClientError as e:
                print(f"❌ Error downloading {remote_path}: {e}")
                return False
        
        if semaphore:
            async with semaphore:
                return await _download()
        else:
            return await _download()
    
    async def close_async(self):
        """Close the async session when done."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def get_device_info(self) -> Dict:
        """Get basic device information."""
        try:
            response = requests.get(self.remote_root, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            return {
                "ip": self.ip_address,
                "port": self.port,
                "url": self.remote_root,
                "status": "connected"
            }
        except:
            return {
                "ip": self.ip_address,
                "port": self.port,
                "url": self.remote_root, 
                "status": "disconnected"
            }
    
    def convert_to_pdf(self, file_or_dir: str, output_path: Optional[str] = None, vectorize: bool = True) -> bool:
        """
        Convert downloaded .note files to PDF.
        
        Args:
            file_or_dir: Local file or directory path containing .note files
            output_path: Output path for PDF(s) 
            vectorize: Use vector format for high quality (default: True)
            
        Returns:
            True if conversion successful, False otherwise
        """
        local_path = self.cache_dir / file_or_dir.lstrip('/')
        
        if not local_path.exists():
            print(f"❌ Local file not found: {local_path}")
            print("💡 Tip: Download the file first with 'supynote download'")
            return False
        
        converter = PDFConverter(vectorize=vectorize, enable_links=True)
        
        if local_path.is_file():
            output = Path(output_path) if output_path else None
            return converter.convert_file(local_path, output)
        elif local_path.is_dir():
            output_dir = Path(output_path) if output_path else None
            success, total = converter.convert_directory(local_path, output_dir)
            return success > 0
        
        return False
    
    def download_and_convert(self, remote_path: str, output_dir: Optional[str] = None, vectorize: bool = True) -> bool:
        """
        Download a file/directory and convert .note files to PDF in one step.
        
        Args:
            remote_path: Remote file or directory path
            output_dir: Local output directory
            vectorize: Use vector format for high quality (default: True)
            
        Returns:    
            True if both download and conversion successful
        """
        # Download first
        if "/" in remote_path and not remote_path.endswith("/"):
            success = self.download_file(remote_path)
            if not success:
                return False
            
            if remote_path.lower().endswith('.note'):
                # Convert single file
                local_file = self.local_root / remote_path.lstrip('/')
                converter = PDFConverter(vectorize=vectorize, enable_links=True)
                return converter.convert_file(local_file)
        else:
            # Download directory
            self.download_directory(remote_path)
            
            # Convert all .note files in the directory
            local_dir = self.local_root / remote_path.lstrip('/')
            converter = PDFConverter(vectorize=vectorize, enable_links=True)
            success, total = converter.convert_directory(local_dir)
            return success > 0
        
        return True