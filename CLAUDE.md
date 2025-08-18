# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation and Setup
```bash
# Install with uv (recommended)
uv sync
pip install -e .

# Or with pip
pip install -e .
```

### Testing the CLI
```bash
# Run the CLI directly
python -m supynote.cli find
supynote find

# Test specific commands
supynote list
supynote download Note
supynote download Note --async --workers 30  # High-performance async download
supynote download Note --convert-pdf --workers 20 --conversion-workers 8  # Parallel download + conversion
supynote convert Note/ --workers 8  # Parallel PDF conversion
supynote convert file.note
```

## Code Architecture

This is a Python CLI tool for interacting with Supernote e-ink tablet devices over the local network.

### Core Components

**CLI Entry Point (`cli.py:main`)**
- Main command parser using argparse with subcommands: find, list, download, convert, browse, info
- Handles global options: --ip, --port, --output
- Device discovery via `find_device()` before most operations

**Device Interface (`supernote.py:Supernote`)**
- Core class for device communication via HTTP requests
- Methods: `list_files()`, `download_file()`, `download_directory()`, `get_device_info()`
- **High-performance async methods**: `download_directory_async()` with connection pooling and semaphore-controlled concurrency
- Uses BeautifulSoup to parse device web interface HTML and extract JSON data
- Supports both multithreaded (sync) and async/await (high-performance) downloads
- Async version uses aiohttp with TCP connection pooling, keep-alive, and streaming file I/O

**Network Discovery (`device_finder.py`)**
- Scans local /24 network for devices listening on port 8089
- Uses concurrent socket connections for fast network scanning
- Function: `find_device()` returns IP address or None

**PDF Conversion (`converter.py:PDFConverter`)**
- Converts Supernote .note files to PDF using `supernotelib` dependency
- **Parallel processing**: `convert_directory()` with ThreadPoolExecutor for batch conversions
- Supports vector (high-quality) and raster formats
- Options for hyperlinks, recursive directory processing
- Methods: `convert_file()`, `convert_directory()`, `convert_files_batch()`

### Data Flow

1. **Device Discovery**: CLI → `find_device()` → network scan → IP address
2. **File Operations**: CLI → `Supernote(ip)` → HTTP requests → device web interface
3. **Downloads**: Device listing → parallel file downloads → local filesystem
4. **Conversion**: Local .note files → `supernotelib` → PDF output

### Key Dependencies

- `requests` + `beautifulsoup4`: Device HTTP communication and HTML parsing
- `aiohttp` + `aiofiles`: High-performance async HTTP with connection pooling (optional but recommended)
- `supernotelib>=0.6.0`: Proprietary .note file format conversion to PDF
- Built-in: `concurrent.futures`, `pathlib`, `argparse`, `asyncio`

### Performance Notes

- **Default async mode**: Downloads use async by default with 20 concurrent connections
- **Connection pooling**: Async version reuses HTTP connections for better performance
- **Memory efficient streaming**: Large files are streamed to disk rather than loaded into memory
- **Configurable concurrency**: Use `--workers N` to control concurrent download limit

### File Structure Patterns

- Downloads default to `./data/` directory
- Maintains remote directory structure in local downloads
- PDF conversion preserves relative paths when processing directories
- All paths use `pathlib.Path` for cross-platform compatibility