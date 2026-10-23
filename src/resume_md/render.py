from __future__ import annotations

import re
from pathlib import Path

from resume_md.model import (
    BulletList,
    Company,
    HorizontalRule,
    Paragraph,
    Resume,
    Row,
    SkillGroup,
)
from resume_md.parse import parse_resume

_TEMPLATE_PATH = Path(__file__).with_name("template.html")

# Default stack. Existing resumes render with this unless --font or front matter overrides it.
DEFAULT_FONT_FAMILY = 'Cambria, Palatino, "Palatino Linotype", Georgia, serif'

_FONT_FORBIDDEN = re.compile(r"[{}<>;\\\n\r]")

# Already a CSS generic. A lone one is the fallback, so nothing is appended.
_GENERIC_FAMILIES = frozenset(
    {
        "serif",
        "sans-serif",
        "monospace",
        "cursive",
        "fantasy",
        "system-ui",
        "ui-serif",
        "ui-sans-serif",
        "ui-monospace",
        "ui-rounded",
        "emoji",
        "math",
        "fangsong",
    }
)

# Single names that should fall back to serif. Anything else (unless it
# contains "mono" or ends with "serif") falls back to sans-serif.
_SERIF_FAMILIES = frozenset(
    {
        "baskerville",
        "bodoni",
        "book antiqua",
        "bookman",
        "cambria",
        "cambria math",
        "century schoolbook",
        "charter",
        "constantia",
        "didot",
        "garamond",
        "georgia",
        "hoefler text",
        "iowan old style",
        "libre baskerville",
        "liberation serif",
        "merriweather",
        "nimbus roman",
        "palatino",
        "palatino linotype",
        "pt serif",
        "source serif",
        "times",
        "times new roman",
    }
)


def _generic_fallback(family: str) -> str | None:
    """Generic to append after one family, or None when it is already generic."""
    key = family.strip().lower()
    if key in _GENERIC_FAMILIES:
        return None
    if "mono" in key:
        return "monospace"
    if key in _SERIF_FAMILIES or key.endswith(" serif"):
        return "serif"
    return "sans-serif"


def _quote_family(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token
    if any(ch.isspace() for ch in token):
        return f'"{token}"'
    return token


def css_font_family(value: str | None) -> str:
    """Return a CSS ``font-family`` list. None selects the Cambria stack.

    A comma means the caller supplied the full stack, which is returned
    unchanged. A single family is quoted when it contains spaces, then a
    generic fallback is appended: ``monospace`` if the name contains "mono",
    ``serif`` for known serif faces and names ending in "serif", and
    ``sans-serif`` otherwise. A lone generic family is left as given.
    """
    if value is None:
        return DEFAULT_FONT_FAMILY
    text = value.strip()
    if not text:
        raise ValueError("font family is empty")
    if _FONT_FORBIDDEN.search(text):
        raise ValueError(f"invalid font family: {text!r}")
    if "," in text:
        return text
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        inner = text[1:-1].strip()
    else:
        inner = text
    if not inner:
        raise ValueError("font family is empty")
    quoted = _quote_family(text)
    fallback = _generic_fallback(inner)
    if fallback is None:
        return quoted
    return f"{quoted}, {fallback}"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    """Render **bold** and _italic_ / *italic* without eating C++."""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                out.append("<strong>" + esc(text[i + 2 : end]) + "</strong>")
                i = end + 2
                continue
        ch = text[i]
        if ch in "_*":
            end = text.find(ch, i + 1)
            if end != -1 and (ch != "*" or not text.startswith("**", i)):
                out.append("<em>" + esc(text[i + 1 : end]) + "</em>")
                i = end + 1
                continue
        j = i + 1
        while j < n and text[j] not in "*_":
            j += 1
        out.append(esc(text[i:j]))
        i = j
    return "".join(out)


def _row_html(left: str, right: str, italic: bool) -> str:
    cls = "left italic" if italic else "left"
    return (
        f'<div class="row"><span class="{cls}">{inline(left)}</span>'
        f'<span class="right">{inline(right)}</span></div>'
    )


def _ul_html(items: list[str]) -> str:
    lis = "\n".join(f"<li>{inline(item)}</li>" for item in items)
    return f"<ul>\n{lis}\n</ul>"


def render_body(resume: Resume) -> str:
    parts = [
        f"<h1>{esc(resume.name)}</h1>",
        f'<p class="contact">{" ◆ ".join(esc(part) for part in resume.contact)}</p>',
    ]
    for section in resume.sections:
        parts.append(f"<h2>{esc(section.title)}</h2>")
        for block in section.blocks:
            if isinstance(block, Paragraph):
                parts.append(f"<p>{inline(block.text)}</p>")
            elif isinstance(block, Row):
                parts.append(_row_html(block.left, block.right, block.left_italic))
            elif isinstance(block, BulletList):
                parts.append(_ul_html(block.items))
            elif isinstance(block, HorizontalRule):
                parts.append("<hr>")
            elif isinstance(block, Company):
                parts.append(f"<h3>{esc(block.name)}</h3>")
                for role in block.roles:
                    parts.append(_row_html(role.left, role.right, role.left_italic))
                    if role.bullets:
                        parts.append(_ul_html(role.bullets))
            elif isinstance(block, SkillGroup):
                parts.append(f"<h4>{esc(block.name)}</h4>")
                if block.bullets:
                    parts.append(_ul_html(block.bullets))
                elif block.body:
                    parts.append(f"<p>{inline(block.body)}</p>")
    return "\n".join(parts)


def render_html(resume: Resume, *, font_family: str | None = None) -> str:
    chosen = font_family if font_family is not None else resume.font
    family = css_font_family(chosen)
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    template = template.replace("{{ font_family }}", family)
    return (
        template.replace("{{ title }}", esc(resume.name))
        .replace("{{ body }}", render_body(resume))
        .replace("{{ name }}", esc(resume.name))
    )


def markdown_to_html(markdown: str, *, font: str | None = None) -> str:
    """Render markdown. ``font`` overrides front-matter ``font`` when given."""
    return render_html(parse_resume(markdown), font_family=font)
