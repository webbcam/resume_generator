from pathlib import Path

import pytest
from tests.helpers import minimal_pdf

from resume_md.pdf import pdf_page_count, write_png_preview


def test_pdf_page_count_ignores_pages_tree_and_pagemode(tmp_path: Path):
    for pages in (1, 2, 3):
        path = tmp_path / f"{pages}.pdf"
        path.write_bytes(minimal_pdf(pages))
        assert pdf_page_count(path) == pages


def test_pdf_page_count_rejects_non_pdf(tmp_path: Path):
    path = tmp_path / "notes.pdf"
    path.write_bytes(b"hello")
    with pytest.raises(ValueError, match="not a PDF"):
        pdf_page_count(path)


def test_pdf_page_count_rejects_pdf_without_page_objects(tmp_path: Path):
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"%PDF-1.4\n% no pages\n%%EOF\n")
    with pytest.raises(ValueError, match="could not determine page count"):
        pdf_page_count(path)


def test_preview_requires_pdftoppm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(minimal_pdf(1))
    with pytest.raises(FileNotFoundError, match="pdftoppm"):
        write_png_preview(pdf, tmp_path / "a.png")
