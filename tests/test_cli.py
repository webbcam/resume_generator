import subprocess
import sys
from pathlib import Path


def test_cli_html_only_writes_expected_strings(tmp_path: Path):
    src = tmp_path / "resume.md"
    src.write_text(
        "# Ada Lovelace\n\nLondon · (555) 010-9999 · ada@example.com\n\n"
        "## Profile\n\nMathematician.\n",
        encoding="utf-8",
    )
    out = tmp_path / "resume.html"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "resume_md",
            "render",
            str(src),
            "--html-only",
            "-o",
            str(out),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out.is_file()
    html = out.read_text(encoding="utf-8")
    assert "Ada Lovelace" in html
    assert "ada@example.com" in html
    assert "◆" in html
    assert "Mathematician." in html


def test_cli_missing_input_fails():
    result = subprocess.run(
        [sys.executable, "-m", "resume_md", "render", "missing.md", "--html-only", "-o", "x.html"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
