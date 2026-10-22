from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

# A page object is `/Type /Page` not followed by more name characters, so
# `/Type /Pages` and `/Type /PageMode` do not count.
_PAGE_OBJECT = re.compile(rb"/Type\s*/Page(?![\w])")

PREVIEW_DPI = "110"


def pdf_page_count(path: Path) -> int:
    """Return the number of pages in a Chrome-style PDF.

    Counts uncompressed ``/Type /Page`` objects. Raises ``ValueError`` when the
    file is not a PDF or no page objects are visible.
    """
    path = Path(path)
    data = path.read_bytes()
    if not data.startswith(b"%PDF"):
        raise ValueError(f"{path} is not a PDF")
    count = len(_PAGE_OBJECT.findall(data))
    if count <= 0:
        raise ValueError(f"could not determine page count of {path}")
    return count


def write_png_preview(
    pdf_path: Path,
    png_path: Path,
    *,
    pdftoppm: str | None = None,
    dpi: str = PREVIEW_DPI,
) -> None:
    """Write a PNG of the first PDF page using ``pdftoppm``."""
    binary = pdftoppm or shutil.which("pdftoppm")
    if not binary:
        raise FileNotFoundError(
            "pdftoppm not found. Install poppler-utils to use --preview."
        )
    pdf_path = Path(pdf_path)
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = png_path.with_suffix("")
    result = subprocess.run(
        [
            binary,
            "-png",
            "-r",
            dpi,
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            str(pdf_path),
            str(prefix),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    produced = Path(str(prefix) + ".png")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        message = f"pdftoppm failed with exit {result.returncode}"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message)
    if produced != png_path and produced.is_file():
        produced.replace(png_path)
    if not png_path.is_file() or png_path.stat().st_size == 0:
        raise RuntimeError(f"preview was not written: {png_path}")
