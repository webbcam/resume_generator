from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from resume_md.chrome import DEFAULT_TIMEOUT_SECONDS, ChromeError, print_pdf
from resume_md.pdf import pdf_page_count, write_png_preview
from resume_md.render import markdown_to_html


def _positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number of seconds") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return value


def resolve_timeout(cli_value: float | None) -> float:
    """``--timeout`` wins, then ``RESUME_MD_TIMEOUT``, then 180 seconds."""
    if cli_value is not None:
        return cli_value
    raw = os.environ.get("RESUME_MD_TIMEOUT")
    if raw is None or raw.strip() == "":
        return float(DEFAULT_TIMEOUT_SECONDS)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"RESUME_MD_TIMEOUT must be a positive number of seconds, got {raw!r}"
        ) from exc
    if value <= 0:
        raise ValueError(f"RESUME_MD_TIMEOUT must be positive, got {raw!r}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-md",
        description="Render a Markdown resume to print-ready HTML and PDF.",
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
    render.add_argument(
        "--font",
        help=(
            "CSS font-family value. Overrides front-matter font. "
            "A single family gets a generic fallback "
            "(serif, monospace, or sans-serif); "
            "a comma-separated stack is used as given. "
            'Default: Cambria, Palatino, "Palatino Linotype", Georgia, serif. '
            "Example: --font '\"Example Sans\", sans-serif'"
        ),
    )
    render.add_argument(
        "--timeout",
        type=_positive_float,
        default=None,
        metavar="SECONDS",
        help=(
            "Kill Chrome if printing takes longer than this "
            "(default: $RESUME_MD_TIMEOUT or 180)"
        ),
    )
    render.add_argument(
        "--max-pages",
        type=_positive_int,
        default=None,
        metavar="N",
        help=(
            "Exit non-zero if the PDF has more than N pages. "
            "The PDF is still written."
        ),
    )
    render.add_argument(
        "--preview",
        metavar="PNG",
        help="Also write a first-page PNG at this path (requires pdftoppm)",
    )
    return parser


def _page_line(path: Path, pages: int | None, size: int) -> str:
    if pages is None:
        return f"{path}: unknown page count ({size} bytes)"
    unit = "page" if pages == 1 else "pages"
    return f"{path}: {pages} {unit} ({size} bytes)"


def _report_chrome_error(exc: ChromeError) -> int:
    print(f"resume-md: {exc}", file=sys.stderr)
    if exc.log:
        print(exc.log, file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.html_only and args.max_pages is not None:
        print(
            "resume-md: --max-pages applies to PDF output; omit --html-only",
            file=sys.stderr,
        )
        return 1
    if args.html_only and args.preview:
        print(
            "resume-md: --preview applies to PDF output; omit --html-only",
            file=sys.stderr,
        )
        return 1

    src = Path(args.input)
    if not src.is_file():
        print(f"resume-md: input not found: {src}", file=sys.stderr)
        return 1
    try:
        html = markdown_to_html(src.read_text(encoding="utf-8"), font=args.font)
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
        timeout = resolve_timeout(args.timeout)
    except ValueError as exc:
        print(f"resume-md: {exc}", file=sys.stderr)
        return 1

    try:
        print_pdf(html_path, out, timeout=timeout)
    except ChromeError as exc:
        return _report_chrome_error(exc)

    pages: int | None
    try:
        pages = pdf_page_count(out)
    except ValueError as exc:
        print(f"resume-md: {exc}", file=sys.stderr)
        pages = None

    size = out.stat().st_size
    print(_page_line(out, pages, size))

    exit_code = 0
    if args.max_pages is not None:
        if pages is None:
            print(
                f"resume-md: could not determine the page count of {out}",
                file=sys.stderr,
            )
            exit_code = 1
        elif pages > args.max_pages:
            unit = "page" if pages == 1 else "pages"
            print(
                f"resume-md: {out} is {pages} {unit}, exceeding --max-pages {args.max_pages}",
                file=sys.stderr,
            )
            exit_code = 1

    if args.preview:
        try:
            write_png_preview(out, Path(args.preview))
        except (FileNotFoundError, RuntimeError, OSError) as exc:
            print(f"resume-md: {exc}", file=sys.stderr)
            return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
