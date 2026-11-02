# AGENTS.md

## Overview
This is a Python project for converting PDF files to JPG images using PyMuPDF (fitz). The project includes a main executable (`main.exe`) built with PyInstaller.

## Build Commands
- **Build executable**: `pyinstaller main.spec`
- **Run main script**: `python main.py`
- **Build folder**: `build/`
- **Dist folder**: `dist/`

## Code Style Guidelines

### General Python Style
- Follow PEP 8 style guidelines
- Use 4-space indentation
- Maximum line length of 79 characters

### Imports
- Standard library imports first (os, sys, etc.)
- Third-party imports第二 (fitz, numpy, etc.)
- Relative imports last if applicable
- Import each module on separate lines

### Naming Conventions
- Functions: `snake_case` (e.g., `pdf_to_jpg`, `batch_convert_pdf_to_jpg`)
- Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

### Error Handling
- Use try-except blocks for file operations
- Validate file paths exist before processing
- Handle PDF parsing exceptions

### Type Hints
- Add type hints to function signatures where helpful
- Use `os.PathLike` for file paths
- Return types should be specified

### File Operations
- Use context managers (`with` statements) for file operations
- Create output directories with `os.makedirs(output_folder, exist_ok=True)`

## Current Code Structure
- **main.py**: Core PDF to JPG conversion logic
  - `pdf_to_jpg()`: Converts a single PDF to JPG
  - `batch_convert_pdf_to_jpg()`: Batch processes PDF files
- **main.spec**: PyInstaller build configuration

## Running Tests
No formal test suite exists. To test:
1. Place PDF files in the `PDF/` folder
2. Run `python main.py`
3. Check `JPG/` folder for converted images
