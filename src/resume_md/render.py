from __future__ import annotations

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


def render_html(resume: Resume) -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{ title }}", esc(resume.name))
        .replace("{{ body }}", render_body(resume))
        .replace("{{ name }}", esc(resume.name))
    )


def markdown_to_html(markdown: str) -> str:
    return render_html(parse_resume(markdown))
