import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple, Union

import fitz  # PyMuPDF
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

INPUT_FOLDER = "PDF"
OUTPUT_FOLDER = "JPG"
DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
MIN_IMAGE_PIXELS = 100_000

FRONT_KEYWORDS = (
    "REPUBLIC OF INDIA",
    "GIVEN NAME",
    "SURNAME",
    "DATE OF BIRTH",
    "PLACE OF BIRTH",
    "DATE OF EXPIRY",
    "NATIONALITY",
    "PASSPORT NO",
    "P<IND",
    "<<<",
)

BACK_KEYWORDS = (
    "NAME OF FATHER",
    "LEGAL GUARDIAN",
    "NAME OF MOTHER",
    "NAME OF SPOUSE",
    "ADDRESS",
    "OLD PASSPORT",
    "FILE NO",
    "PIN:",
)

EXCLUDE_KEYWORDS = (
    "INCOME TAX DEPARTMENT",
    "INCOMETAX DEPARTMENT",
    "PERMANENT ACCOUNT NUMBER",
)

console = Console()


def get_tesseract_path() -> Optional[str]:
    """
    Locate the Tesseract OCR executable on the system.

    Returns:
        Path to tesseract executable, or None if unavailable
    """
    if os.path.exists(DEFAULT_TESSERACT):
        return DEFAULT_TESSERACT
    return shutil.which("tesseract")


def rotate_pixmap(pix: fitz.Pixmap, k: int) -> fitz.Pixmap:
    """
    Rotate a PyMuPDF Pixmap by 90-degree increments using NumPy.

    Args:
        pix: Source RGB Pixmap without alpha
        k: Number of 90-degree counter-clockwise rotations

    Returns:
        Rotated PyMuPDF Pixmap
    """
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )
    rot = np.rot90(arr, k=k)
    return fitz.Pixmap(
        pix.colorspace,
        rot.shape[1],
        rot.shape[0],
        rot.tobytes(),
        False,
    )


def run_ocr_on_pixmap(pix: fitz.Pixmap, tesseract_cmd: str) -> str:
    """
    Run Tesseract OCR on a Pixmap and return uppercase text.

    Args:
        pix: PyMuPDF Pixmap to OCR
        tesseract_cmd: Path to Tesseract executable

    Returns:
        Extracted uppercase text
    """
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name
        pix.save(tmp_path)
        result = subprocess.run(
            [tesseract_cmd, tmp_path, "stdout", "--psm", "6"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        return result.stdout.upper()
    except OSError:
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def classify_passport_image(
    pdf_document: fitz.Document,
    xref: int,
    tesseract_cmd: Optional[str],
) -> Optional[str]:
    """
    Classify an embedded PDF image as 'front', 'back', or None.

    Checks upright orientation first, then 90-degree rotations if needed.

    Args:
        pdf_document: Open PyMuPDF Document instance
        xref: Image cross-reference number
        tesseract_cmd: Path to Tesseract executable

    Returns:
        'front', 'back', or None if it is another image (photo/PAN/visa)
    """
    if not tesseract_cmd:
        return None

    try:
        pix = fitz.Pixmap(pdf_document, xref)
        if pix.alpha:
            pix = fitz.Pixmap(pix, 0)
        if pix.n > 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        while max(pix.width, pix.height) > 1600:
            pix.shrink(1)
    except (RuntimeError, ValueError):
        return None

    for rot_k in (0, -1, 1):
        test_pix = pix if rot_k == 0 else rotate_pixmap(pix, rot_k)
        text = run_ocr_on_pixmap(test_pix, tesseract_cmd)

        if any(kw in text for kw in EXCLUDE_KEYWORDS):
            return None

        front_score = sum(1 for kw in FRONT_KEYWORDS if kw in text)
        back_score = sum(1 for kw in BACK_KEYWORDS if kw in text)

        if front_score >= 2 and front_score > back_score:
            return "front"
        if back_score >= 2 and back_score > front_score:
            return "back"

    return None


def get_ordered_candidate_xrefs(pdf_document: fitz.Document) -> List[int]:
    """
    Collect candidate embedded image xrefs ordered to check Page 1 and the
    Last Page first, then middle pages.

    Filters out tiny watermark/logo images below MIN_IMAGE_PIXELS.

    Args:
        pdf_document: Open PyMuPDF Document instance

    Returns:
        Ordered list of unique image xrefs
    """
    page_count = pdf_document.page_count
    if page_count == 0:
        return []

    page_order = [0]
    if page_count > 1:
        page_order.append(page_count - 1)
    page_order.extend(range(1, page_count - 1))

    candidates: List[int] = []
    seen = set()

    for page_num in page_order:
        page = pdf_document.load_page(page_num)
        images = page.get_images(full=True)
        valid_imgs = [
            img
            for img in images
            if img[2] * img[3] >= MIN_IMAGE_PIXELS
        ]
        for img in valid_imgs:
            xref = img[0]
            if xref not in seen:
                seen.add(xref)
                candidates.append(xref)

    return candidates


def save_xref_as_jpg(
    pdf_document: fitz.Document,
    xref: int,
    output_path: Path,
) -> bool:
    """
    Extract an embedded image by xref and save it to disk as a JPG.

    Args:
        pdf_document: Open PyMuPDF Document instance
        xref: Image cross-reference number
        output_path: Destination file path

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        base_image = pdf_document.extract_image(xref)
        image_bytes = base_image["image"]
        with open(output_path, "wb") as file_obj:
            file_obj.write(image_bytes)
        return True
    except (OSError, RuntimeError, ValueError, KeyError) as err:
        console.print(
            f"[bold red]Error saving {output_path.name}:[/bold red] {err}"
        )
        return False


def pdf_to_jpg(
    pdf_path: Union[str, os.PathLike],
    output_folder: Union[str, os.PathLike],
) -> Tuple[int, int]:
    """
    Detect and extract the passport front and back images from a PDF and
    save them as '<PDF_Filename>_front.jpg' and '<PDF_Filename>_back.jpg'.

    Args:
        pdf_path: Path to the PDF file
        output_folder: Path to the output folder

    Returns:
        Tuple of (page_count, images_saved)
    """
    pdf_path = Path(pdf_path)
    output_folder = Path(output_folder)

    if not pdf_path.is_file():
        console.print(
            f"[bold red]Error:[/bold red] File not found: {pdf_path}"
        )
        return 0, 0

    try:
        os.makedirs(output_folder, exist_ok=True)
    except OSError as err:
        console.print(
            f"[bold red]Error creating output folder:[/bold red] {err}"
        )
        return 0, 0

    tesseract_cmd = get_tesseract_path()

    try:
        with fitz.open(pdf_path) as pdf_document:
            page_count = pdf_document.page_count
            if page_count == 0:
                console.print(
                    f"[yellow]Warning:[/yellow] {pdf_path.name} has no pages."
                )
                return 0, 0

            candidates = get_ordered_candidate_xrefs(pdf_document)
            found: Dict[str, int] = {}

            for xref in candidates:
                side = classify_passport_image(
                    pdf_document, xref, tesseract_cmd
                )
                if side and side not in found:
                    found[side] = xref
                if "front" in found and "back" in found:
                    break

            if not tesseract_cmd and candidates:
                found.setdefault("front", candidates[0])
                if len(candidates) > 1:
                    found.setdefault("back", candidates[1])

            base_name = pdf_path.stem
            images_saved = 0

            for side in ("front", "back"):
                if side in found:
                    out_path = output_folder / f"{base_name}_{side}.jpg"
                    if save_xref_as_jpg(pdf_document, found[side], out_path):
                        images_saved += 1
                else:
                    console.print(
                        f"[yellow]Warning:[/yellow] Could not find passport "
                        f"{side} in {pdf_path.name}"
                    )
    except Exception as err:
        console.print(
            f"[bold red]Error processing PDF:[/bold red] "
            f"{pdf_path.name} - {err}"
        )
        return 0, 0

    console.print(
        f"[green][OK][/green] Saved [bold]{images_saved}[/bold] image(s) "
        f"from [bold]{pdf_path.name}[/bold]"
    )
    return page_count, images_saved


def batch_convert_pdf_to_jpg(
    input_folder: Union[str, os.PathLike],
    output_folder: Union[str, os.PathLike],
) -> None:
    """
    Batch convert all passport PDF files in a folder to front/back JPGs.

    Args:
        input_folder: Path to the folder containing PDF files
        output_folder: Path to the output folder
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    if not input_path.exists() or not input_path.is_dir():
        console.print(
            Panel.fit(
                f"[red]Input folder not found: {input_path}[/red]",
                title="Error",
            )
        )
        return

    try:
        os.makedirs(output_path, exist_ok=True)
    except OSError as err:
        console.print(
            f"[bold red]Error creating output folder:[/bold red] {err}"
        )
        return

    pdf_files = sorted(input_path.glob("*.pdf"))

    if not pdf_files:
        console.print(
            Panel.fit(
                "[yellow]No PDF files found in the input folder[/yellow]",
                title="Warning",
            )
        )
        return

    table = Table(title="Passport PDF to JPG Conversion Summary")
    table.add_column("PDF File", style="cyan")
    table.add_column("Total Pages", style="magenta", justify="right")
    table.add_column("Images Saved", style="green", justify="right")

    total_pages = 0
    total_images = 0

    with Progress(
        SpinnerColumn(spinner_name="line"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Converting PDFs...", total=len(pdf_files))

        for pdf_path in pdf_files:
            page_count, images_saved = pdf_to_jpg(pdf_path, output_path)

            table.add_row(
                pdf_path.name,
                str(page_count),
                str(images_saved),
            )

            total_pages += page_count
            total_images += images_saved
            progress.advance(task)

    console.print("\n")
    console.print(table)
    console.print(
        Panel.fit(
            f"[bold green]Successfully processed {len(pdf_files)} "
            f"PDF file(s)![/bold green]\n"
            f"Total PDF pages scanned: [bold]{total_pages}[/bold]\n"
            f"Total images saved: [bold]{total_images}[/bold]\n"
            f"Output folder: [bold]{output_path.resolve()}[/bold]",
            title="Conversion Complete",
            border_style="green",
        )
    )


if __name__ == "__main__":
    batch_convert_pdf_to_jpg(INPUT_FOLDER, OUTPUT_FOLDER)
