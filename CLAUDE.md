# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A deterministic (no LLM) Markdown → HTML/PDF resume renderer. It parses a specific Markdown dialect (documented in README.md) into a Cambria-styled, one-page, print-ready resume matching a Word-style layout — not a generic "apply-pack" HTML resume.

## Commands

```bash
uv sync --group dev                    # install deps
make test                              # == uv run pytest (no Chrome required)
uv run ruff check src tests            # lint (make lint)
uv run pytest tests/test_render.py -k test_role_row_is_left_italic_and_right_date  # single test
uv run pytest --update-golden          # explicitly refresh tests/golden/sample.html after an intentional render change
uv run resume-md render resume.md -o resume.pdf
uv run resume-md render resume.md --html-only -o resume.html   # skip Chrome
```

Chrome PDF tests are marked `@pytest.mark.chrome` and skip automatically if Chrome isn't installed; Chrome is located via `CHROME` env var or `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` (see `chrome.py`).

## Architecture

Pipeline is strictly one-directional, each stage in its own module under `src/resume_md/`:

```
parse.py (Markdown text -> model.py dataclasses) -> render.py (dataclasses -> HTML string via template.html) -> cli.py (HTML -> file, optionally shells out to Chrome headless for PDF)
```

- **model.py** — plain dataclasses (`Resume`, `Section`, `Company`, `Role`, `SkillGroup`, `Row`, `Paragraph`, `BulletList`, `HorizontalRule`) forming the intermediate representation. `Block` is a union type used inside `Section.blocks`.
- **parse.py** — a hand-rolled line-by-line state machine (`parse_resume`), not a general Markdown parser. State (`section`/`company`/`skill`/`role`) tracks which heading level was last opened so that list items and `left | right` rows attach to the correct parent. Heading level dictates structure: H1=name, H2=section, H3=employer (opens a `Company`), H4=skill group (opens a `SkillGroup`). A bare line containing ` | ` is a `Row`, split on the **last** occurrence, with left-side italics detected from `_..._`/`*...*` wrapping. A line of `---`/`***`/`___` is a `HorizontalRule`.
- **render.py** — turns the model back into HTML. `inline()` implements a minimal, hand-rolled `**bold**`/`_italic_`/`*italic*` scanner deliberately written so `C++` is never treated as emphasis markers. `render_html` string-replaces `{{ title }}`/`{{ body }}`/`{{ name }}` placeholders in `template.html` (no templating engine).
- **template.html** — contains the actual print CSS (Cambria font stack, `@page` letter-size rules, point sizes). Changes to visual styling live here, not in Python.
- **chrome.py** — locates a Chrome/Chromium binary across platforms.
- **cli.py** — argparse-based `render` subcommand; writes HTML, then optionally shells out to headless Chrome (`--print-to-pdf`) unless `--html-only`.

The Markdown dialect itself (contact-line splitting on ` · `/` | `, H1–H4 semantics, row splitting rules) is documented with an example in README.md — read that before changing `parse.py`, since the dialect is intentionally narrow and any change is a contract change.

## Testing conventions

- `tests/golden/sample.html` is a snapshot of `examples/sample.md` rendered to HTML. It is compared byte-for-byte in `test_golden_html_snapshot`; only regenerate it with `--update-golden` when a render change is intentional.
- `examples/sample.md` is a fictional fixture — never commit a real personal resume (`examples/private.md` is gitignored).
- CLI tests (`tests/test_cli.py`) invoke the module via `subprocess` + `python -m resume_md`, not by calling `main()` in-process.
