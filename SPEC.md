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

CSS `font-family: Cambria, Palatino, "Palatino Linotype", Georgia, serif`. Do not embed a subset TTF extracted from the PDF (missing glyphs).

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
- Lists are bullets. `**bold**` and `_italic_` work as usual.
- A line of `---`, `***`, or `___` inside a section is a horizontal rule. Section heads do not draw a rule unless you insert one.
- No YAML required for v1.

A fictional fixture lives in `examples/sample.md`. Real personal resumes stay local and gitignored (`examples/private.md`). Do not commit them.

## Pipeline (deterministic — no LLM)

1. Parse Markdown → HTML with the dialect above.
2. Wrap in a print stylesheet (`src/resume_md/template.html` + CSS).
3. Write HTML next to the PDF (or `--html`).
4. Print PDF via Chrome/Chromium headless:

```
"$CHROME" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf=OUT.pdf file://ABS.html
```

Detect Chrome at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` and `CHROME` env. `--html-only` skips Chrome (tests use this).

CLI:

```
resume-md render resume.md -o resume.pdf
resume-md render resume.md --html-only -o resume.html
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
