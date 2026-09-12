from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from resume_md.chrome import default_chrome_path
from resume_md.render import markdown_to_html


def print_pdf(html_path: Path, pdf_path: Path, chrome: str | None = None) -> None:
    binary = chrome or default_chrome_path()
    if not binary:
        raise FileNotFoundError(
            "Chrome/Chromium not found. Set CHROME or install Google Chrome. "
            "Use --html-only to skip PDF."
        )
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        binary,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path.resolve()}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-md",
        description="Render a Markdown resume to Cambria-styled HTML and PDF.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    render = sub.add_parser("render", help="Render Markdown to HTML/PDF")
    render.add_argument("input", help="Path to resume Markdown")
    render.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output PDF (or HTML with --html-only)",
    )
    render.add_argument(
        "--html-only",
        action="store_true",
        help="Skip Chrome and write HTML to -o",
    )
    render.add_argument(
        "--html",
        dest="html_path",
        help="HTML output path (default: next to the PDF, same stem)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    src = Path(args.input)
    if not src.is_file():
        print(f"resume-md: input not found: {src}", file=sys.stderr)
        return 1
    try:
        html = markdown_to_html(src.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"resume-md: {exc}", file=sys.stderr)
        return 1

    out = Path(args.output)
    if args.html_only:
        html_path = out
    elif args.html_path:
        html_path = Path(args.html_path)
    else:
        html_path = out.with_suffix(".html")

    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")

    if args.html_only:
        return 0

    try:
        print_pdf(html_path, out)
    except FileNotFoundError as exc:
        print(f"resume-md: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"resume-md: Chrome failed with exit {exc.returncode}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
