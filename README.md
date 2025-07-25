# Supynote CLI

A simple, clean CLI tool to interact with your Supernote device.

## Features

- 🔍 **Auto-discovery**: Automatically find your Supernote on the network
- 📂 **File listing**: Browse files and directories on your device
- ⬇️ **Download**: Download individual files or entire directories  
- 📄 **PDF conversion**: Convert .note files to high-quality vector PDFs
- 🌐 **Web interface**: Open the device web interface in your browser
- ⚡ **Fast downloads**: Multithreaded downloads for speed

## Installation

```bash
# Clone and install
git clone <repo-url>
cd supynote-cli
pip install -e .
```

## Quick Start

```bash
# Find your Supernote device
supynote find

# List all files
supynote list

# List files in Note directory
supynote list Note

# Download Note directory
supynote download Note

# Download a specific file
supynote download Note/my-note.note

# Convert .note file to PDF (vector format)
supynote convert my-note.note

# Convert all .note files in a directory
supynote convert Note/

# Open device web interface
supynote browse

# Show device info
supynote info
```

## Commands

### `supynote find`
Scan the local network to find your Supernote device.
- `--open`: Open the device web interface after finding it

### `supynote list [directory]`
List files and directories on the device.

### `supynote download <path>`
Download files or directories from the device.
- `--workers N`: Number of parallel download workers (default: 4)
- `--convert-pdf`: Automatically convert downloaded .note files to PDF

### `supynote convert <path>`
Convert .note files to PDF format (vector by default).
- `--output DIR`: Output directory or specific file path
- `--no-vector`: Use raster format instead of vector
- `--no-links`: Disable hyperlinks in PDF output
- `--recursive`: Process subdirectories (default: true)

### `supynote browse`
Open the device web interface in your default browser.

### `supynote info`
Show device connection information.

## Options

- `--ip IP`: Manually specify device IP address
- `--port PORT`: Device port (default: 8089)
- `--output DIR`: Local output directory for downloads

## Examples

```bash
# Find device and open in browser
supynote find --open

# Download with custom output directory
supynote download Note --output ~/my-notes

# Use specific IP address
supynote --ip 192.168.1.100 list

# Download with more workers for speed
supynote download EXPORT --workers 8

# Download and convert to PDF in one step  
supynote download Note --convert-pdf

# Convert with custom output directory
supynote convert Note/ --output ~/my-pdfs

# Convert single file with specific output name
supynote convert my-note.note --output my-document.pdf
```