# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-05

### Initial Release

This is the first public release of supynote-cli, a command-line tool for interacting with Supernote e-ink tablets over local network.

#### Features
- **Device Discovery**: Auto-discovery of Supernote devices on local network
- **File Management**: List and browse files on device
- **High-Performance Downloads**: Parallel async downloads with configurable workers (20-30x faster than sync)
- **PDF Conversion**: Convert .note files to high-quality vector PDFs using supernotelib
- **OCR Support**: Multiple OCR engines for handwritten text recognition
  - Native text extraction (default, fast)
  - TrOCR (Microsoft, handwriting-optimized)
  - LLaVA (via Ollama, advanced)
  - Gemini API integration
- **Date-Based Merging**: Automatically merge PDFs by date with markdown generation
- **Apple Silicon Support**: MPS acceleration for OCR on M1/M2/M3/M4 Macs
- **CLI Commands**: find, list, download, convert, ocr, merge, browse, info, validate

#### Architecture
- Domain-Driven Design (DDD) layered architecture
- Separation of concerns: domain, application, infrastructure, presentation layers
- Repository pattern for data access
- Use case driven design
- Type hints throughout codebase

#### Performance
- Async HTTP with connection pooling and keep-alive
- Configurable worker concurrency for downloads and conversions
- Streaming file I/O for memory efficiency with large files
- Parallel PDF conversion with ThreadPoolExecutor
- Smart file size checking to skip unnecessary downloads

#### Documentation
- Comprehensive README with installation, usage, and troubleshooting
- Example automation scripts for Alfred (macOS) and remote sync
- Contributing guidelines and Code of Conduct
- GitHub issue and PR templates
- CI/CD with GitHub Actions

#### Developer Experience
- Modern Python tooling with uv support
- Optional dependencies for OCR features
- Comprehensive test suite (unit and integration)
- Pre-commit hooks compatible
- Multiple Python version support (3.8-3.12)

### Security
- No hardcoded credentials or personal data
- Environment variable support for configuration
- Secure network communication over local network only

---

## Future Releases

See [GitHub Issues](https://github.com/r4tb/supynote-cli/issues) for planned features and improvements.
