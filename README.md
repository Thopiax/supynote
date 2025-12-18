# Supynote CLI

A simple, clean CLI tool to interact with your Supernote device.

## Requirements

- Python 3.8.1+
- Supernote device connected to same local network
- Device must have "Export via LAN" enabled (Settings → System → Export via LAN)

### System Dependencies (for PDF conversion)

PDF conversion requires the Cairo graphics library. Install it before installing supynote:

**macOS:**
```bash
brew install cairo pkg-config
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y libcairo2-dev pkg-config python3-dev
```

**Windows:**
No additional dependencies needed (pre-built wheels available)

### Optional Features
- **OCR**: Requires additional dependencies (transformers, torch) - see Installation
- **Apple Silicon**: OCR automatically uses MPS acceleration on M1/M2/M3/M4 Macs

## Features

- 🔍 **Auto-discovery**: Automatically find your Supernote on the network
- 📂 **File listing**: Browse files and directories on your device
- ⬇️ **Download**: Download individual files or entire directories  
- 📄 **PDF conversion**: Convert .note files to high-quality vector PDFs
- 🌐 **Web interface**: Open the device web interface in your browser
- ⚡ **Fast downloads**: Multithreaded downloads for speed

## Installation

### From PyPI (Recommended)

```bash
# Basic installation
pip install supynote

# With OCR features
pip install supynote[ocr]
```

### From Source (Development)

```bash
# Clone and install
git clone https://github.com/thopiax/supynote.git
cd supynote
pip install -e .

# With OCR features
pip install -e .[ocr]
```

### Using uv (For Development)

```bash
uv sync  # Installs all dependencies including dev tools
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

## Environment Variables

Configure supynote-cli behavior with these environment variables:

- `SUPYNOTE_JOURNALS_DIR`: Default directory for markdown journal exports (used by `merge` command)
- `SUPYNOTE_IP`: Default device IP (alternative to `--ip` flag)
- `SUPYNOTE_OUTPUT_DIR`: Default output directory (alternative to `--output` flag)

Example `.env` file:
```bash
SUPYNOTE_JOURNALS_DIR=$HOME/Documents/journals
SUPYNOTE_IP=192.168.1.100
```

Load with: `export $(cat .env | xargs)`

See `examples/automation/.env.example` for more configuration options.

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

## Troubleshooting

### PDF Conversion Errors
- **Error: "cairo not found"** or **"pycairo build failed"**
  - Install Cairo system dependencies (see System Dependencies section above)
  - macOS: `brew install cairo pkg-config`
  - Linux: `sudo apt-get install libcairo2-dev pkg-config python3-dev`
- After installing Cairo, reinstall supynote: `pip install --force-reinstall supynote`

### Device Not Found
- Ensure device is on same network as computer
- Try manually specifying IP: `supynote --ip YOUR_IP list`
- Some networks block device discovery - use `--ip` flag with your device's IP address

### OCR Not Working
- Install OCR dependencies: `pip install -e .[ocr]`
- First run downloads ML models (~500MB) - may take time
- Requires internet connection for initial model download
- On Apple Silicon, ensure MPS is available (macOS 12.3+)

### Slow Performance
- Increase workers: `supynote download --workers 30`
- Use async mode (default in v1.0+)
- OCR is CPU/GPU intensive - fewer workers may help on older machines
- Check network connection quality

### Permission Errors
- Ensure output directory is writable
- On macOS, you may need to grant Terminal full disk access
- Check firewall settings aren't blocking network discovery

For more help, see [GitHub Issues](https://github.com/thopiax/supynote/issues)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Steps:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Acknowledgments

- **Supernote Team**: For creating excellent e-ink tablets that inspire tools like this
- **[supernotelib](https://github.com/jya-dev/supernotelib)**: Unofficial library for .note file conversion - the foundation of PDF conversion in this tool
- **Claude Code**: This project was built with significant assistance from Claude Code, which handled much of the heavy lifting in development and refactoring
- **TrOCR** (Microsoft) and **LLaVA**: Powering the OCR capabilities for handwritten text recognition