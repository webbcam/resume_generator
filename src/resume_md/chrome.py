from __future__ import annotations

import os
import shutil
from pathlib import Path

MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


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
