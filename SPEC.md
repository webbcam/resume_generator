# resume-md — implementation spec

Deterministic Markdown → Cambria HTML/PDF resume renderer. Target is a one-page Word-style layout, not a Georgia “apply-pack” HTML resume.

## Visual target

Typography:

| Element | Font | Size |
|---------|------|------|
| Name | Cambria | 24pt, centered |
| Contact line | Cambria | 9pt, centered; separators are ◆ (U+25C6) |
| Section heads (`Profile`, `Professional Experience`, …) | Cambria Bold | 10pt, no automatic underline |
| Company (`Amazon`) | Cambria Bold | 12pt |
| Role title | Cambria Italic | 9pt, left |
| Dates | Cambria | 9pt, right, same baseline as role |
| Body / bullets | Cambria | 9pt, line-height ~1.22 |
| Skill group labels | Cambria Bold | 9pt |
| Page | US Letter | content starts ~0.25–0.45in from edges |

CSS `font-family` defaults to `Cambria, Palatino, "Palatino Linotype", Georgia, serif`. Override the whole list with `--font` or front-matter `font` (below). Do not embed a subset TTF extracted from the PDF (missing glyphs).

## Markdown dialect (document in README)

```markdown
# Full Name

City, ST · (555) 555-5555 · you@example.com · github.com/you

## Profile

---

Paragraph.

## Professional Experience

---

### Company

_Job title_ | Mon. YYYY – Present

- Bullet
- Bullet

_Another title at same company_ | Summer YYYY

- Bullet

## Education

**School - College** | City, ST

Degree (BS) | Month YYYY

GPA: 3.5

## Technical Skills

#### Group name

- Item

#### Group with inline body (no list)

One-line skills, comma-separated.
```

Rules:

- H1 = name.
- First paragraph after H1 = contact. Split on ` · ` (also accept ` | `). Join with ` ◆ ` in HTML.
- H2 = section, H3 = employer, H4 = skill group.
- A **non-list, non-heading** line containing ` | ` is a left/right row (role/date or school/location). Split on the **last** ` | `. Italic left if the source used `_…_` / `*…*`.
- Lists are bullets. A marker (`-`, `*`, or `+`) followed by one or more spaces or tabs is a bullet, including two or more spaces (`-  item`) or a tab. A hyphen with no following whitespace (`-item`) is a paragraph.
- `**bold**` and `_italic_` work as usual.
- A line of `---`, `***`, or `___` inside a section is a horizontal rule. Section heads do not draw a rule unless you insert one.
- HTML comments are stripped before parsing. `<!-- ... -->` may sit inline or span lines. Adjacent spaces and tabs collapse to one space; newlines outside the comment stay, so a comment on its own line does not join the lines around it. Comments do not nest (the first `-->` closes). An unclosed `<!--` is an error and names its line. Comment text must not appear in the HTML.
- Front matter is optional. If the file begins with a `---` fence, the only key is `font`, whose value is a CSS `font-family` list (a single family with spaces is quoted automatically). Unknown keys, a repeated `font`, an empty value, or a missing closing `---` are errors. The closing fence is the next line that is exactly `---`; later rules inside sections are unchanged. `--font` overrides the front-matter value. When neither is set, the Cambria stack above is used, on both `body` and `h1`.

A fictional fixture lives in `examples/sample.md`. Real personal resumes stay local and gitignored (`examples/private.md`). Do not commit them.

## Pipeline (deterministic — no LLM)

1. Parse Markdown → HTML with the dialect above.
2. Wrap in a print stylesheet (`src/resume_md/template.html` + CSS).
3. Write HTML next to the PDF (or `--html`).
4. Print PDF via Chrome/Chromium headless. Detect Chrome at `CHROME`, then `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, then `google-chrome`, `chromium`, `chromium-browser`, or `chrome` on `PATH`. `--html-only` skips Chrome (tests use this).

The print command always includes:

- `--headless=new`
- `--disable-gpu`
- `--disable-dev-shm-usage`
- `--disable-software-rasterizer`
- `--disable-extensions`
- `--disable-background-networking`
- `--disable-component-update`
- `--disable-features=OptimizationGuideModelDownloading,OptimizationHints,Translate,MediaRouter`
- `--disable-sync`
- `--metrics-recording-only`
- `--no-first-run`
- `--no-default-browser-check`
- `--no-pdf-header-footer`
- `--user-data-dir` set to a fresh temporary directory (so a running Chrome profile is not reused)
- `--print-to-pdf` of a partial file, moved into place only after a non-empty `%PDF` header is present
- the `file://` URL of the HTML

`--timeout SECONDS` (else `RESUME_MD_TIMEOUT`, else 180) bounds the run. On timeout the CLI sends SIGTERM to the Chrome process tree, then SIGKILL if it is still alive after 10 seconds. If Chrome writes a non-empty PDF and does not exit (for example because a launcher left a debugging port open), the CLI keeps that PDF and stops the process tree instead of waiting out the timeout. A missing, empty, or non-PDF result is an error even when Chrome exits 0; dbus noise on stderr is not, if the PDF was written. A previous PDF at the output path is left untouched when the new run fails.

On success the CLI prints `PATH: 1 page (BYTES bytes)` or `PATH: N pages (BYTES bytes)`. `--max-pages N` exits non-zero, after the PDF is written, when the page count is greater than N. `--preview PNG` also writes a 110 dpi PNG of page 1 via `pdftoppm`.

CLI:

```
resume-md render resume.md -o resume.pdf
resume-md render resume.md --html-only -o resume.html
resume-md render resume.md -o resume.pdf --font '"Example Sans", sans-serif' --max-pages 1
resume-md render resume.md -o resume.pdf --preview resume.png --timeout 60
```

Python package: `pyproject.toml`, `src/resume_md/`, `uv`/`pip` installable, `python -m resume_md`.

## Tests (required — this is the bar)

Use **pytest**. Tests must run **without Chrome**.

Minimum:

1. **Parse/render unit tests** for contact diamonds, `|` rows, nested company titles, H4 skill groups, C++ not eaten by Markdown.
2. **Golden HTML snapshot** of `examples/sample.md` (or `tests/fixtures/sample.md`) — pytest-regressions or file compare under `tests/golden/sample.html`. Update via an explicit flag, not silently.
3. **CLI test** invoking `resume-md render --html-only` on a temp file; assert exit 0 and expected strings in HTML.
4. **Optional** `@pytest.mark.chrome` PDF test: if Chrome exists, render PDF and `pypdf`/`pymupdf` extract_text contains name + email; skip if Chrome missing.

`make test` or `pytest` in CI-ready form. Include a GitHub Actions workflow that runs pytest (no Chrome required).

## Repo hygiene

- README: weekend workflow (edit md → `uv run resume-md render resume.md`) and dialect.
- `.gitignore`: `__pycache__`, `.venv`, generated `*.pdf` / `*.html`, personal drafts.
- `LICENSE` MIT.
- Ruff or equivalent.

## Done when

- `pytest` passes.
- `resume-md render examples/sample.md --html-only` produces sensible HTML.
- If Chrome is available, `resume-md render examples/sample.md -o /tmp/sample.pdf` produces a letter PDF.
- README explains the markdown dialect with a copy-paste example.
