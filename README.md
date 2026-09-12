# resume-md

Weekend workflow: edit a Markdown resume, then print a one-page PDF that matches a Cambria Word layout (not a Georgia “apply-pack” HTML resume).

```bash
uv run resume-md render resume.md -o resume.pdf
uv run resume-md render resume.md --html-only -o resume.html
```

HTML is written next to the PDF (same stem) unless you pass `--html path`. `--html-only` skips Chrome. Chrome is detected at `CHROME` or `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.

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
- Lists are bullets. `**bold**` and `_italic_` work as usual.
- A line of `---`, `***`, or `___` inside a section is a horizontal rule (`<hr>`). Section heads do not draw a rule unless you insert one.
- No YAML front matter in v1.

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
