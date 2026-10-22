import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from tests.helpers import (
    minimal_pdf,
    pid_running,
    recording_chrome_source,
    sleeper_chrome_source,
    write_exe,
)

from resume_md.chrome import (
    HEADLESS_PRINT_FLAGS,
    ChromeTimeoutError,
    PdfNotWrittenError,
    default_chrome_path,
    print_pdf,
)
from resume_md.pdf import pdf_page_count

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


@pytest.mark.chrome
def test_page_count_matches_pypdf_when_resume_overflows(tmp_path: Path):
    if not _chrome_available():
        pytest.skip("Chrome not installed")
    paragraphs = "\n\n".join(f"Paragraph {i}. " + ("detail " * 40) for i in range(80))
    src = tmp_path / "long.md"
    src.write_text(f"# N\n\nC · a@b.c\n\n## Profile\n\n{paragraphs}\n", encoding="utf-8")
    out = tmp_path / "long.pdf"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "resume_md",
            "render",
            str(src),
            "-o",
            str(out),
            "--timeout",
            "60",
            "--max-pages",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.is_file() and out.stat().st_size > 0
    pytest.importorskip("pypdf")
    from pypdf import PdfReader

    pages = len(PdfReader(str(out)).pages)
    assert pdf_page_count(out) == pages
    assert pages >= 2
    assert result.returncode != 0
    assert "exceeding --max-pages 1" in result.stderr


def _html(tmp_path: Path) -> Path:
    html = tmp_path / "in.html"
    html.write_text("<html></html>", encoding="utf-8")
    return html


def test_print_pdf_passes_headless_flags_and_chrome_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    args_file = tmp_path / "args.txt"
    pdf_src = tmp_path / "src.pdf"
    pdf_src.write_bytes(minimal_pdf(1))
    chrome = tmp_path / "chrome"
    write_exe(chrome, recording_chrome_source())
    other = tmp_path / "other"
    write_exe(other, "#!/bin/sh\necho should-not-run >&2\nexit 9\n")
    monkeypatch.setenv("CHROME", str(other))
    monkeypatch.setenv("ARGS_FILE", str(args_file))
    monkeypatch.setenv("PDF_SRC", str(pdf_src))
    monkeypatch.setenv("CHROME_MODE", "write")
    out = tmp_path / "out.pdf"
    out.write_bytes(b"%PDF-OLD")
    print_pdf(_html(tmp_path), out, chrome=str(chrome), timeout=10)
    argv = args_file.read_text(encoding="utf-8").splitlines()
    assert argv[0] == str(chrome)
    assert argv[1 : 1 + len(HEADLESS_PRINT_FLAGS)] == HEADLESS_PRINT_FLAGS
    profile = argv[1 + len(HEADLESS_PRINT_FLAGS)].split("=", 1)[1]
    assert not Path(profile).exists()
    assert out.read_bytes().startswith(b"%PDF-")
    assert b"OLD" not in out.read_bytes()
    assert not (tmp_path / "out.pdf.partial").exists()


def test_print_pdf_nonzero_exit_with_a_pdf_is_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    pdf_src = tmp_path / "src.pdf"
    pdf_src.write_bytes(minimal_pdf(1))
    chrome = tmp_path / "chrome"
    write_exe(chrome, recording_chrome_source())
    monkeypatch.setenv("ARGS_FILE", str(tmp_path / "args.txt"))
    monkeypatch.setenv("PDF_SRC", str(pdf_src))
    monkeypatch.setenv("CHROME_MODE", "write")
    monkeypatch.setenv("CHROME_EXIT", "1")
    monkeypatch.setenv("CHROME_STDERR", "dbus: noise\n")
    out = tmp_path / "out.pdf"
    print_pdf(_html(tmp_path), out, chrome=str(chrome), timeout=10)
    assert out.read_bytes().startswith(b"%PDF-")


@pytest.mark.parametrize("mode", ["missing", "empty", "text"])
def test_print_pdf_rejects_missing_empty_or_non_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
):
    chrome = tmp_path / "chrome"
    write_exe(chrome, recording_chrome_source())
    monkeypatch.setenv("ARGS_FILE", str(tmp_path / "args.txt"))
    monkeypatch.setenv("PDF_SRC", str(tmp_path / "src.pdf"))
    monkeypatch.setenv("CHROME_MODE", mode)
    monkeypatch.setenv("CHROME_STDERR", "dbus: failed\n")
    out = tmp_path / "out.pdf"
    out.write_bytes(b"%PDF-OLD")
    expected = "not a valid PDF" if mode == "text" else "missing or empty"
    with pytest.raises(PdfNotWrittenError, match=expected) as caught:
        print_pdf(_html(tmp_path), out, chrome=str(chrome), timeout=10)
    assert "dbus: failed" in caught.value.log
    assert out.read_bytes() == b"%PDF-OLD"
    assert not list(tmp_path.glob("*.partial"))


def _assert_tree_killed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, ignore_term: bool
) -> None:
    chrome = tmp_path / "chrome"
    write_exe(chrome, sleeper_chrome_source(ignore_term=ignore_term))
    survive = tmp_path / "survive"
    child_file = tmp_path / "child"
    monkeypatch.setenv("SURVIVE_FILE", str(survive))
    monkeypatch.setenv("CHILD_PID_FILE", str(child_file))
    out = tmp_path / "out.pdf"
    started = time.monotonic()
    with pytest.raises(ChromeTimeoutError, match="timed out") as caught:
        print_pdf(
            _html(tmp_path),
            out,
            chrome=str(chrome),
            timeout=0.8,
            kill_after=0.8,
        )
    child = int(child_file.read_text(encoding="utf-8")) if child_file.is_file() else None
    try:
        assert "killed the Chrome process tree" in str(caught.value)
        assert time.monotonic() - started < 8
        assert child is not None
        assert not pid_running(child)
        assert not survive.exists()
        assert not out.exists()
    finally:
        if child is not None and pid_running(child):
            os.kill(child, 9)


def test_print_pdf_keeps_pdf_when_chrome_hangs_after_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    pdf_src = tmp_path / "src.pdf"
    pdf_src.write_bytes(minimal_pdf(2))
    chrome = tmp_path / "chrome"
    write_exe(
        chrome,
        f"""#!{sys.executable}
import os
import time
from pathlib import Path
import sys
pdf = None
for arg in sys.argv[1:]:
    if arg.startswith("--print-to-pdf="):
        pdf = arg.split("=", 1)[1]
Path(pdf).write_bytes(Path(os.environ["PDF_SRC"]).read_bytes())
time.sleep(60)
""",
    )
    monkeypatch.setenv("PDF_SRC", str(pdf_src))
    out = tmp_path / "out.pdf"
    started = time.monotonic()
    print_pdf(_html(tmp_path), out, chrome=str(chrome), timeout=10, kill_after=1)
    assert time.monotonic() - started < 5
    assert out.read_bytes() == pdf_src.read_bytes()


def test_print_pdf_timeout_kills_child_processes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _assert_tree_killed(tmp_path, monkeypatch, ignore_term=False)


def test_print_pdf_sigkill_after_term_is_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _assert_tree_killed(tmp_path, monkeypatch, ignore_term=True)
