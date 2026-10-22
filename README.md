# resume-md

Weekend workflow: edit a Markdown resume, then print a one-page PDF that matches a Cambria Word layout (not a Georgia “apply-pack” HTML resume).

```bash
uv run resume-md render resume.md -o resume.pdf
uv run resume-md render resume.md --html-only -o resume.html
```

HTML is written next to the PDF (same stem) unless you pass `--html path`. `--html-only` skips Chrome. Chrome is `CHROME`, Google Chrome on macOS, or `google-chrome` / `chromium` on `PATH`.

```bash
uv run resume-md render resume.md -o resume.pdf --max-pages 1
uv run resume-md render resume.md -o resume.pdf --font '"Example Sans", sans-serif'
uv run resume-md render resume.md -o resume.pdf --preview resume.png --timeout 60
```

`--font` is a CSS `font-family` value and overrides front matter. The default is the Cambria stack, so existing resumes do not change. A single family (no comma) gets a generic fallback: `serif` for known serif faces (such as Georgia, Cambria, Palatino, and Times New Roman) and for names ending in "serif", `monospace` when the name contains "mono", and `sans-serif` otherwise. A comma-separated stack is used exactly as written. `--timeout` (or `RESUME_MD_TIMEOUT`, default 180) kills Chrome, including its child processes, if printing stalls. A missing or empty PDF is an error even when Chrome exits 0. After a successful print the CLI reports the page count (`resume.pdf: 1 page (12345 bytes)`). `--max-pages N` still writes the PDF, then exits non-zero when the PDF is longer than N. Check the exit code: a PDF on disk does not mean the page limit was met. `--preview` writes a first-page PNG and needs `pdftoppm`.

## Markdown dialect

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

- H1 is the name.
- The first paragraph after H1 is contact. Split on ` · ` (also accept ` | `). Joined with ` ◆ ` in HTML.
- H2 is a section, H3 is an employer, H4 is a skill group.
- A non-list, non-heading line containing ` | ` is a left/right row (role/date or school/location). Split on the **last** ` | `. The left side is italic if the source used `_…_` or `*…*`.
- Lists are bullets. The marker (`-`, `*`, or `+`) is followed by one or more spaces or tabs, so `-  item` is still a bullet.
- `**bold**` and `_italic_` work as usual.
- A line of `---`, `***`, or `___` inside a section is a horizontal rule (`<hr>`). Section heads do not draw a rule unless you insert one.
- HTML comments (`<!-- ... -->`) are stripped, including comments that span lines. They do not nest. An unclosed `<!--` is an error that reports the line. A comment is not resume text, so `<!--` in a line will not appear in the output.
- Front matter is optional. A leading `---` fence may set `font` to a CSS `font-family` value. A single family gets the same generic fallback as `--font`; a comma-separated stack is kept as written. No other keys are read. Without it, the Cambria stack is used.

```markdown
---
font: "Example Sans", sans-serif
---
```

A fictional fixture lives at `examples/sample.md`. Do not commit a real personal resume (`examples/private.md` is gitignored).

## Develop

```bash
uv sync --group dev
make test          # pytest; Chrome not required
uv run ruff check src tests
uv run pytest --update-golden   # refresh tests/golden/sample.html
```

Optional: `@pytest.mark.chrome` renders a PDF and checks extracted text when Chrome is installed.

Installable as `python -m resume_md` or the `resume-md` console script.
