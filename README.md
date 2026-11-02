# PDF-JPG V2.0 — Passport Front & Back Extractor

A Python utility that batch-processes passport PDF files and extracts only the **Passport Front** (bio/MRZ page) and **Passport Back** (address/family details page) as `<PDF_Filename>_front.jpg` and `<PDF_Filename>_back.jpg`.

---

## Features

- **Smart OCR Page & Image Classification:**
  - Uses **PyMuPDF (`fitz`)** and **Tesseract OCR** to automatically identify the **Passport Front** and **Passport Back** images inside each PDF.
  - Handles **rotated scans** (90° clockwise and counter-clockwise) automatically.
  - Supports multi-image pages (e.g., when both front and back scans are embedded on the same PDF page).
- **Automatic Non-Passport Filtering:**
  - Skips intermediate blank visa pages and stamped visa pages.
  - Ignores portrait/headshot photos and PAN cards (`Income Tax Department` / `Permanent Account Number`) bundled in the same PDF.
  - Filters out small scanner watermark logos (`< 100,000` pixels).
- **Rich Terminal Progress & Summary:**
  - Displays live batch conversion progress and a summary table using `rich`.

---

## Project Structure

```text
PDF-JPG_V2.0/
├── PDF/           # Input folder: place passport PDF files here
├── JPG/           # Output folder: generated <Name>_front.jpg and <Name>_back.jpg
├── main.py        # Core passport front/back detection and extraction script
├── main.spec      # PyInstaller configuration for building main.exe
├── AGENTS.md      # Project coding standards and guidelines
└── README.md      # Project documentation
```

---

## Prerequisites

- **Python 3.11+**
- **Tesseract OCR** installed on Windows (default path: `C:\Program Files\Tesseract-OCR\tesseract.exe` or available on `PATH`)
- **Python Dependencies:**
  - `PyMuPDF` (`fitz`)
  - `numpy`
  - `rich`
  - `pyinstaller` *(optional, for building the standalone executable)*

Install Python dependencies:

```powershell
pip install PyMuPDF numpy rich pyinstaller
```

---

## Usage

### 1. Run with Python
1. Place one or more passport PDF files inside the `PDF/` folder.
2. Run the script:
   ```powershell
   python main.py
   ```
3. Converted images will be saved in the `JPG/` folder as:
   - `<PDF_Filename>_front.jpg`
   - `<PDF_Filename>_back.jpg`

### 2. Run Standalone Executable (`main.exe`)
Double-click `main.exe` or run it from PowerShell in the project root directory:

```powershell
.\main.exe
```

---

## Building the Executable

To rebuild `main.exe` using PyInstaller:

```powershell
pyinstaller --noconfirm main.spec
Copy-Item -Path "dist\main.exe" -Destination "main.exe" -Force
```
