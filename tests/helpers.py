"""Fixtures shared by CLI and Chrome tests. Not a personal resume."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def write_exe(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def minimal_pdf(pages: int = 1) -> bytes:
    """A tiny PDF whose page objects are visible to the byte scanner."""
    kids = " ".join(f"{index + 3} 0 R" for index in range(pages))
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        f"2 0 obj << /Type /Pages /Count {pages} /Kids [{kids}] >> endobj\n",
        "% decoy /Type /Pages /Type /PageMode must not count as pages\n",
    ]
    for index in range(pages):
        objects.append(
            f"{index + 3} 0 obj << /Type /Page /Parent 2 0 R "
            "/MediaBox [0 0 612 792] >> endobj\n"
        )
    body = "".join(objects)
    return f"%PDF-1.4\n{body}trailer << /Root 1 0 R >>\n%%EOF\n".encode()


def recording_chrome_source() -> str:
    return f"""#!{sys.executable}
import os
import sys
from pathlib import Path

Path(os.environ["ARGS_FILE"]).write_text("\\n".join(sys.argv))
pdf = None
for arg in sys.argv[1:]:
    if arg.startswith("--print-to-pdf="):
        pdf = arg.split("=", 1)[1]
mode = os.environ.get("CHROME_MODE", "write")
if pdf and mode == "write":
    Path(pdf).write_bytes(Path(os.environ["PDF_SRC"]).read_bytes())
elif pdf and mode == "empty":
    Path(pdf).write_bytes(b"")
elif pdf and mode == "text":
    Path(pdf).write_bytes(b"not a pdf")
message = os.environ.get("CHROME_STDERR", "")
if message:
    sys.stderr.write(message)
raise SystemExit(int(os.environ.get("CHROME_EXIT", "0")))
"""


def sleeper_chrome_source(*, ignore_term: bool) -> str:
    ignore = "import signal\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\n" if ignore_term else ""
    child_ignore = (
        "    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n" if ignore_term else ""
    )
    return f"""#!{sys.executable}
import os
import time
from pathlib import Path
{ignore}
pid = os.fork()
if pid == 0:
{child_ignore}    time.sleep(60)
    Path(os.environ["SURVIVE_FILE"]).write_text("survived")
    os._exit(0)
Path(os.environ["CHILD_PID_FILE"]).write_text(str(pid))
time.sleep(60)
"""


def pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    stat = Path(f"/proc/{pid}/stat")
    try:
        raw = stat.read_text(encoding="utf-8")
    except OSError:
        return True
    rparen = raw.rfind(")")
    if rparen < 0:
        return True
    state = raw[rparen + 2 :].split(maxsplit=1)[0]
    return state not in {"Z", "X"}
