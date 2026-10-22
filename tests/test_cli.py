import os
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

from resume_md.chrome import HEADLESS_PRINT_FLAGS
from resume_md.cli import resolve_timeout

ROOT = Path(__file__).resolve().parents[1]


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
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


def _run_cli(
    args: list[str], *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, "-m", "resume_md", *args],
        cwd=ROOT,
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def test_resolve_timeout_prefers_flag_then_env():
    monkey_env = os.environ.copy()
    os.environ.pop("RESUME_MD_TIMEOUT", None)
    try:
        assert resolve_timeout(None) == 180
        assert resolve_timeout(12) == 12
        os.environ["RESUME_MD_TIMEOUT"] = "30"
        assert resolve_timeout(None) == 30
        assert resolve_timeout(5) == 5
        os.environ["RESUME_MD_TIMEOUT"] = "nope"
        with pytest.raises(ValueError, match="RESUME_MD_TIMEOUT"):
            resolve_timeout(None)
        os.environ["RESUME_MD_TIMEOUT"] = "0"
        with pytest.raises(ValueError, match="positive"):
            resolve_timeout(None)
    finally:
        os.environ.clear()
        os.environ.update(monkey_env)


def test_cli_strips_comments_keeps_wide_bullets_and_applies_font(tmp_path: Path):
    src = tmp_path / "resume.md"
    src.write_text(
        "---\nfont: Georgia\n---\n"
        "# Jane Doe <!-- draft -->\n\n"
        "Example City · jane@example.com <!-- old -->\n\n"
        "## Profile\n\n"
        "<!-- TODO -->\n\n"
        "-  two spaces\n"
        "- one space\n\n"
        "Hello <!-- secret --> there.\n",
        encoding="utf-8",
    )
    out = tmp_path / "resume.html"
    result = _run_cli(["render", str(src), "--html-only", "-o", str(out)])
    assert result.returncode == 0, result.stderr
    html = out.read_text(encoding="utf-8")
    assert "font-family: Georgia, serif" in html
    assert "Cambria, Palatino" not in html
    assert "<li>two spaces</li>" in html
    assert "<li>one space</li>" in html
    assert "Hello there." in html
    for hidden in ("TODO", "secret", "draft", "<!--", "old -->"):
        assert hidden not in html

    overridden = tmp_path / "override.html"
    result = _run_cli(
        ["render", str(src), "--html-only", "-o", str(overridden), "--font", "Example Sans"]
    )
    assert result.returncode == 0, result.stderr
    html = overridden.read_text(encoding="utf-8")
    assert 'font-family: "Example Sans", sans-serif' in html
    assert "Georgia" not in html


def test_cli_unclosed_comment_fails(tmp_path: Path):
    src = tmp_path / "resume.md"
    src.write_text("# Jane\n\nCity · a@b.c\n\n<!-- oops\n", encoding="utf-8")
    result = _run_cli(["render", str(src), "--html-only", "-o", str(tmp_path / "out.html")])
    assert result.returncode != 0
    assert "unclosed HTML comment" in result.stderr


def test_cli_html_only_rejects_pdf_flags(tmp_path: Path):
    src = tmp_path / "resume.md"
    src.write_text("# Jane\n\nCity · a@b.c\n", encoding="utf-8")
    out = tmp_path / "out.html"
    pages = _run_cli(["render", str(src), "--html-only", "-o", str(out), "--max-pages", "1"])
    assert pages.returncode != 0
    assert "--max-pages" in pages.stderr
    preview = _run_cli(
        ["render", str(src), "--html-only", "-o", str(out), "--preview", str(tmp_path / "p.png")]
    )
    assert preview.returncode != 0
    assert "--preview" in preview.stderr


def test_cli_html_only_ignores_invalid_timeout_env(tmp_path: Path):
    src = tmp_path / "resume.md"
    src.write_text("# Jane\n\nCity · a@b.c\n", encoding="utf-8")
    result = _run_cli(
        ["render", str(src), "--html-only", "-o", str(tmp_path / "out.html")],
        env={"RESUME_MD_TIMEOUT": "nope"},
    )
    assert result.returncode == 0, result.stderr


def _resume(tmp_path: Path) -> Path:
    src = tmp_path / "resume.md"
    src.write_text("# Jane Doe\n\nExample City · jane@example.com\n", encoding="utf-8")
    return src


def _recording_chrome(tmp_path: Path, pdf_bytes: bytes) -> tuple[Path, Path, dict[str, str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    chrome = bin_dir / "chrome"
    write_exe(chrome, recording_chrome_source())
    pdf_src = tmp_path / "src.pdf"
    pdf_src.write_bytes(pdf_bytes)
    args_file = tmp_path / "args.txt"
    env = {
        "CHROME": str(chrome),
        "ARGS_FILE": str(args_file),
        "PDF_SRC": str(pdf_src),
        "CHROME_MODE": "write",
        "CHROME_EXIT": "0",
    }
    return chrome, args_file, env


def test_cli_reports_page_count_and_passes_headless_flags(tmp_path: Path):
    _chrome, args_file, env = _recording_chrome(tmp_path, minimal_pdf(1))
    out = tmp_path / "resume.pdf"
    result = _run_cli(
        ["render", str(_resume(tmp_path)), "-o", str(out), "--timeout", "30"],
        env={**env, "RESUME_MD_TIMEOUT": "nope"},
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert f"{out}: 1 page (" in result.stdout
    assert "1 pages" not in result.stdout
    argv = args_file.read_text(encoding="utf-8").splitlines()
    assert argv[1 : 1 + len(HEADLESS_PRINT_FLAGS)] == HEADLESS_PRINT_FLAGS
    assert argv[1 + len(HEADLESS_PRINT_FLAGS)].startswith("--user-data-dir=")
    assert "--headless" not in argv
    assert out.is_file() and out.stat().st_size > 0


def test_cli_max_pages_keeps_the_pdf_and_fails(tmp_path: Path):
    _chrome, _args, env = _recording_chrome(tmp_path, minimal_pdf(2))
    out = tmp_path / "resume.pdf"
    over = _run_cli(
        ["render", str(_resume(tmp_path)), "-o", str(out), "--max-pages", "1"],
        env=env,
    )
    assert over.returncode != 0
    assert "2 pages" in over.stdout
    assert "exceeding --max-pages 1" in over.stderr
    assert out.is_file() and out.stat().st_size > 0

    ok = _run_cli(
        ["render", str(_resume(tmp_path)), "-o", str(out), "--max-pages", "2"],
        env=env,
    )
    assert ok.returncode == 0, ok.stderr
    assert "2 pages" in ok.stdout


def test_cli_missing_pdf_is_an_error_even_on_exit_zero(tmp_path: Path):
    _chrome, _args, env = _recording_chrome(tmp_path, minimal_pdf(1))
    env["CHROME_MODE"] = "missing"
    env["CHROME_STDERR"] = "dbus: failed to connect\n"
    out = tmp_path / "resume.pdf"
    out.write_bytes(b"%PDF-OLD")
    result = _run_cli(["render", str(_resume(tmp_path)), "-o", str(out)], env=env)
    assert result.returncode != 0
    assert "missing or empty" in result.stderr
    assert "dbus: failed to connect" in result.stderr
    assert out.read_bytes() == b"%PDF-OLD"


def test_cli_timeout_kills_the_chrome_tree(tmp_path: Path):
    chrome = tmp_path / "chrome"
    write_exe(chrome, sleeper_chrome_source(ignore_term=False))
    survive = tmp_path / "survive"
    child_file = tmp_path / "child"
    out = tmp_path / "resume.pdf"
    started = time.monotonic()
    result = _run_cli(
        ["render", str(_resume(tmp_path)), "-o", str(out), "--timeout", "1"],
        env={
            "CHROME": str(chrome),
            "SURVIVE_FILE": str(survive),
            "CHILD_PID_FILE": str(child_file),
        },
    )
    elapsed = time.monotonic() - started
    child = int(child_file.read_text(encoding="utf-8")) if child_file.is_file() else None
    try:
        assert result.returncode != 0
        assert "timed out after 1s" in result.stderr
        assert "killed the Chrome process tree" in result.stderr
        assert elapsed < 8
        assert child is not None
        assert not pid_running(child)
        assert not survive.exists()
        assert not out.exists()
    finally:
        if child is not None and pid_running(child):
            os.kill(child, 9)


def test_cli_preview_uses_pdftoppm(tmp_path: Path):
    _chrome, _args, env = _recording_chrome(tmp_path, minimal_pdf(1))
    bin_dir = tmp_path / "bin"
    previewer = bin_dir / "pdftoppm"
    write_exe(
        previewer,
        f"""#!{sys.executable}
import sys
from pathlib import Path
Path(sys.argv[-1] + ".png").write_bytes(b"\\x89PNG\\r\\n\\x1a\\npreview")
Path({str(tmp_path / "ppm-args.txt")!r}).write_text("\\n".join(sys.argv))
""",
    )
    png = tmp_path / "preview.png"
    env["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    result = _run_cli(
        [
            "render",
            str(_resume(tmp_path)),
            "-o",
            str(tmp_path / "resume.pdf"),
            "--preview",
            str(png),
        ],
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert png.read_bytes().startswith(b"\x89PNG")
    ppm_args = (tmp_path / "ppm-args.txt").read_text(encoding="utf-8").splitlines()
    assert "-png" in ppm_args
    assert "-singlefile" in ppm_args
    assert "110" in ppm_args
