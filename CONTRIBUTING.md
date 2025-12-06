# Contributing to supynote-cli

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/r4tb/supynote-cli
   cd supynote-cli
   ```

2. Install dependencies with uv:
   ```bash
   uv sync
   pip install -e .
   ```

3. Run tests:
   ```bash
   pytest
   ```

## Code Style

- Follow PEP 8 for Python code
- Use functional programming patterns where appropriate
- Follow Domain-Driven Design principles (see `changelog/DDD_REFACTORING.md`)
- Prefer `for...of` over `forEach` for iteration
- Use type hints where possible

## Testing

- Add tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage on new code
- Test on multiple Python versions if possible (3.8, 3.9, 3.10, 3.11, 3.12)

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add/update tests as needed
5. Update documentation (README, docstrings)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to your fork (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Refactor, etc.)
- Keep first line under 50 characters
- Add detailed description if needed
- Reference issues when applicable

Examples:
```
Add OCR support for handwritten notes

Update README with environment variable documentation

Fix device discovery on complex network setups
Resolves #42
```

## Development Guidelines

### Adding New Features

1. Check existing issues/PRs to avoid duplication
2. Open an issue to discuss major changes before starting
3. Follow the existing code structure and patterns
4. Document new features in README
5. Add examples if applicable

### Bug Fixes

1. Create a failing test that demonstrates the bug
2. Fix the bug
3. Ensure the test now passes
4. Add comments explaining non-obvious fixes

### Documentation

- Update README for user-facing changes
- Add docstrings to new functions/classes
- Update CHANGELOG.md
- Consider adding examples for complex features

## Architecture

This project follows Domain-Driven Design (DDD) principles:

- **Domain Layer**: Core business logic and entities
- **Application Layer**: Use cases and DTOs
- **Infrastructure Layer**: External integrations (network, file system)
- **Presentation Layer**: CLI interface

See `changelog/DDD_REFACTORING.md` for detailed architecture documentation.

## Testing Requirements

### Unit Tests
- Test individual functions and classes
- Mock external dependencies
- Fast execution

### Integration Tests
- Test component interactions
- May use real file system (in temp directories)
- Test actual device communication when possible

## Questions?

- Open an issue for discussion before starting major changes
- Ask questions in pull request comments
- Check existing issues and documentation first

## Code of Conduct

This project follows the Contributor Covenant Code of Conduct. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.
