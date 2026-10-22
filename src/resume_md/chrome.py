from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path

MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Flags that keep headless print off first-run component and model downloads.
# A temporary --user-data-dir is added per run so Chrome does not attach to an
# already-open profile and exit without writing a PDF.
HEADLESS_PRINT_FLAGS = [
    "--headless=new",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-software-rasterizer",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-features=OptimizationGuideModelDownloading,OptimizationHints,Translate,MediaRouter",
    "--disable-sync",
    "--metrics-recording-only",
    "--no-first-run",
    "--no-default-browser-check",
    "--no-pdf-header-footer",
]

DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_KILL_AFTER_SECONDS = 10
_LOG_TAIL_LINES = 40


class ChromeError(Exception):
    """Chrome failed, timed out, or did not write a PDF."""

    def __init__(self, message: str, *, log: str = "") -> None:
        super().__init__(message)
        self.log = log


class ChromeNotFoundError(ChromeError):
    pass


class ChromeTimeoutError(ChromeError):
    pass


class PdfNotWrittenError(ChromeError):
    pass


def default_chrome_path() -> str | None:
    env = os.environ.get("CHROME")
    if env:
        return env
    if Path(MAC_CHROME).is_file():
        return MAC_CHROME
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _resolve_binary(binary: str) -> str:
    if Path(binary).is_file():
        return binary
    found = shutil.which(binary)
    if found:
        return found
    raise ChromeNotFoundError(
        f"Chrome/Chromium not found: {binary}. Set CHROME or install Google Chrome. "
        "Use --html-only to skip PDF."
    )


def _descendant_pids(root: int) -> list[int]:
    """PIDs in the process tree of ``root``, including ``root`` itself.

    Linux exposes parents through ``/proc``. Other platforms get just ``root``;
    children that stayed in its process group are still reached via ``killpg``.
    """
    proc = Path("/proc")
    if not proc.is_dir():
        return [root]
    children: dict[int, list[int]] = {}
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "stat").read_text()
        except OSError:
            continue
        rparen = raw.rfind(")")
        if rparen < 0:
            continue
        fields = raw[rparen + 2 :].split()
        if len(fields) < 2:
            continue
        try:
            ppid = int(fields[1])
        except ValueError:
            continue
        children.setdefault(ppid, []).append(int(entry.name))

    order: list[int] = []
    stack = [root]
    seen: set[int] = set()
    while stack:
        pid = stack.pop()
        if pid in seen or pid <= 0:
            continue
        seen.add(pid)
        order.append(pid)
        stack.extend(children.get(pid, []))
    return order


def _signal_tree(pid: int, sig: int) -> None:
    """Signal ``pid``, its descendants, and its process group when it leads one.

    ``killpg`` is used only when ``pid`` is the group leader. That is true for
    processes started with ``start_new_session``. It avoids signaling the CLI's
    own group if session setup ever failed.
    """
    if pid <= 1:
        return
    for child in reversed(_descendant_pids(pid)):
        if child <= 1:
            continue
        try:
            os.kill(child, sig)
        except (ProcessLookupError, PermissionError):
            pass
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    if pgid != pid or pgid <= 1:
        return
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def _log_text(stdout: bytes | None, stderr: bytes | None) -> str:
    chunks: list[str] = []
    for data in (stdout, stderr):
        if not data:
            continue
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            chunks.append(text)
    lines = "\n".join(chunks).splitlines()
    if len(lines) > _LOG_TAIL_LINES:
        lines = lines[-_LOG_TAIL_LINES :]
    return "\n".join(lines).strip()


def _pdf_problem(path: Path) -> str | None:
    """None when ``path`` is a non-empty file with a PDF header."""
    try:
        size = path.stat().st_size
    except OSError:
        return "missing or empty"
    if size == 0:
        return "missing or empty"
    try:
        with path.open("rb") as handle:
            header = handle.read(5)
    except OSError:
        return "missing or empty"
    if header != b"%PDF-":
        return "not a valid PDF"
    return None


def print_pdf(
    html_path: Path,
    pdf_path: Path,
    chrome: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    kill_after: float = DEFAULT_KILL_AFTER_SECONDS,
) -> None:
    """Print ``html_path`` to ``pdf_path`` with headless Chrome.

    ``chrome`` overrides the binary (otherwise ``CHROME`` or the platform
    default). ``timeout`` is seconds before the Chrome process tree is killed.
    A missing, empty, or non-PDF result is an error even when Chrome exits 0.
    A non-zero exit that still wrote a PDF is success.
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if kill_after < 0:
        raise ValueError("kill_after must be non-negative")

    chosen = chrome or default_chrome_path()
    if not chosen:
        raise ChromeNotFoundError(
            "Chrome/Chromium not found. Set CHROME or install Google Chrome. "
            "Use --html-only to skip PDF."
        )
    binary = _resolve_binary(chosen)
    html_path = Path(html_path)
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    partial = pdf_path.with_name(pdf_path.name + ".partial")

    profile = Path(tempfile.mkdtemp(prefix="resume-md-chrome-"))
    cmd = [
        binary,
        *HEADLESS_PRINT_FLAGS,
        f"--user-data-dir={profile}",
        f"--print-to-pdf={partial.resolve()}",
        html_path.resolve().as_uri(),
    ]
    try:
        try:
            returncode, log = _run_chrome(
                cmd, partial=partial, timeout=timeout, kill_after=kill_after
            )
        except ChromeTimeoutError as exc:
            raise ChromeTimeoutError(
                f"Chrome timed out after {_format_seconds(timeout)}s while writing {pdf_path}; "
                "killed the Chrome process tree",
                log=exc.log,
            ) from None
        problem = _pdf_problem(partial)
        if problem:
            raise PdfNotWrittenError(
                f"Chrome exited {returncode} but the PDF is {problem}: {pdf_path}",
                log=log,
            )
        try:
            partial.replace(pdf_path)
        except OSError as exc:
            raise ChromeError(f"could not write {pdf_path}: {exc}") from exc
    finally:
        partial.unlink(missing_ok=True)
        shutil.rmtree(profile, ignore_errors=True)


def _drain(pipe: object, parts: list[bytes]) -> None:
    reader = getattr(pipe, "read", None)
    if reader is None:
        return
    while True:
        chunk = reader(4096)
        if not chunk:
            return
        parts.append(chunk)


def _joined(parts: list[bytes]) -> bytes:
    return b"".join(parts)


def _stop_process(proc: subprocess.Popen[bytes], kill_after: float) -> None:
    if proc.poll() is not None:
        return
    _signal_tree(proc.pid, signal.SIGTERM)
    grace = kill_after if kill_after > 0 else 0.1
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        _signal_tree(proc.pid, signal.SIGKILL)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def _run_chrome(
    cmd: list[str],
    *,
    partial: Path,
    timeout: float,
    kill_after: float,
) -> tuple[int, str]:
    """Run Chrome until it exits, the PDF is ready, or ``timeout`` elapses.

    Some Chrome launchers add a debugging port and then stay alive after
    ``--print-to-pdf`` has already written the file. Once the PDF is a
    non-empty ``%PDF`` and has stopped growing (or Chrome reports that it
    wrote the file), the process tree is stopped and the PDF is kept.
    """
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise ChromeNotFoundError(
            f"Chrome/Chromium not found: {cmd[0]}. Set CHROME or install Google Chrome. "
            "Use --html-only to skip PDF."
        ) from exc
    except PermissionError as exc:
        raise ChromeError(f"Chrome is not executable: {cmd[0]}") from exc

    assert proc.stdout is not None and proc.stderr is not None
    stdout_parts: list[bytes] = []
    stderr_parts: list[bytes] = []
    threads = [
        threading.Thread(target=_drain, args=(proc.stdout, stdout_parts), daemon=True),
        threading.Thread(target=_drain, args=(proc.stderr, stderr_parts), daemon=True),
    ]
    for thread in threads:
        thread.start()

    deadline = time.monotonic() + timeout
    last_size = -1
    stable_since: float | None = None
    try:
        while True:
            finished = proc.poll() is not None
            problem = _pdf_problem(partial)
            captured = _joined(stdout_parts) + _joined(stderr_parts)
            wrote = b"bytes written to file" in captured
            if finished or (problem is None and wrote):
                break
            now = time.monotonic()
            if problem is None:
                size = partial.stat().st_size
                if size != last_size:
                    last_size = size
                    stable_since = now
                elif stable_since is not None and now - stable_since >= 0.3:
                    break
            else:
                last_size = -1
                stable_since = None
            if now >= deadline:
                if problem is None:
                    break
                _stop_process(proc, kill_after)
                log = _log_text(_joined(stdout_parts), _joined(stderr_parts))
                raise ChromeTimeoutError(
                    f"Chrome timed out after {_format_seconds(timeout)}s "
                    "and the Chrome process tree was killed",
                    log=log,
                )
            time.sleep(0.05)
        if proc.poll() is None:
            # The PDF is ready, but Chrome did not exit. Keep a copy in case
            # shutting the process down truncates the file.
            ready = partial.read_bytes()
            _stop_process(proc, kill_after)
            partial.write_bytes(ready)
    finally:
        for thread in threads:
            thread.join(timeout=2)

    code = proc.returncode if proc.returncode is not None else 0
    return code, _log_text(_joined(stdout_parts), _joined(stderr_parts))


def _format_seconds(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(value)
