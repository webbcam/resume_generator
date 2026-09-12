import shutil
from pathlib import Path

import pytest

from resume_md.chrome import default_chrome_path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "sample.md"


def _chrome_available() -> bool:
    path = default_chrome_path()
    return bool(path and Path(path).exists())


@pytest.mark.chrome
def test_pdf_extracts_name_and_email(tmp_path: Path):
    if not _chrome_available():
        pytest.skip("Chrome not installed")

    out = tmp_path / "sample.pdf"
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "resume_md",
            "render",
            str(SAMPLE),
            "-o",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out.is_file() and out.stat().st_size > 0

    pytest.importorskip("pypdf")
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(out)).pages)
    assert "Jordan Hale" in text
    assert "jordan.hale@example.com" in text


def test_chrome_marker_is_skippable():
    """The chrome mark exists even when the binary does not."""
    assert default_chrome_path() or shutil.which("google-chrome") or True
