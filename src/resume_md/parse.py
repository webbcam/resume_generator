from __future__ import annotations

import re

from resume_md.model import (
    BulletList,
    Company,
    HorizontalRule,
    Paragraph,
    Resume,
    Role,
    Row,
    Section,
    SkillGroup,
)

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_LIST = re.compile(r"^[-*+]\s+(.*)$")
_HR = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})$")


def split_contact(line: str) -> list[str]:
    if " · " in line:
        parts = line.split(" · ")
    elif " | " in line:
        parts = line.split(" | ")
    else:
        parts = [line]
    return [part.strip() for part in parts if part.strip()]


def parse_row(line: str) -> Row:
    left, right = line.rsplit(" | ", 1)
    left, right = left.strip(), right.strip()
    italic = False
    if len(left) >= 2:
        if left.startswith("_") and left.endswith("_") and not left.startswith("__"):
            left = left[1:-1]
            italic = True
        elif (
            left.startswith("*")
            and left.endswith("*")
            and not left.startswith("**")
            and not left.endswith("**")
        ):
            left = left[1:-1]
            italic = True
    return Row(left=left, right=right, left_italic=italic)


def parse_resume(markdown: str) -> Resume:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    n = len(lines)

    def skip_blank() -> None:
        nonlocal i
        while i < n and not lines[i].strip():
            i += 1

    skip_blank()
    if i >= n:
        raise ValueError("empty resume")
    heading = _HEADING.match(lines[i].strip())
    if not heading or len(heading.group(1)) != 1:
        raise ValueError("resume must start with an H1 name")
    name = heading.group(2).strip()
    i += 1
    skip_blank()
    if i >= n or lines[i].strip().startswith("#"):
        raise ValueError("missing contact line after name")
    contact = split_contact(lines[i].strip())
    i += 1

    sections: list[Section] = []
    section: Section | None = None
    company: Company | None = None
    skill: SkillGroup | None = None
    role: Role | None = None

    def close_company() -> None:
        nonlocal company, role
        company = None
        role = None

    def close_skill() -> None:
        nonlocal skill
        skill = None

    while i < n:
        line = lines[i].strip()
        i += 1
        if not line:
            continue

        heading = _HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if level == 2:
                close_company()
                close_skill()
                section = Section(title=title)
                sections.append(section)
            elif level == 3:
                close_skill()
                if section is None:
                    raise ValueError(f"H3 {title!r} is not inside a section")
                company = Company(name=title)
                role = None
                section.blocks.append(company)
            elif level == 4:
                close_company()
                if section is None:
                    raise ValueError(f"H4 {title!r} is not inside a section")
                skill = SkillGroup(name=title)
                section.blocks.append(skill)
            else:
                raise ValueError(f"unexpected heading level {level}: {title!r}")
            continue

        if _HR.match(line):
            if section is None:
                raise ValueError("horizontal rule outside a section")
            close_company()
            close_skill()
            section.blocks.append(HorizontalRule())
            continue

        listed = _LIST.match(line)
        if listed:
            item = listed.group(1).strip()
            if role is not None:
                role.bullets.append(item)
            elif skill is not None:
                skill.bullets.append(item)
            elif section is not None:
                last = section.blocks[-1] if section.blocks else None
                if isinstance(last, BulletList):
                    last.items.append(item)
                else:
                    section.blocks.append(BulletList(items=[item]))
            else:
                raise ValueError(f"list item outside a section: {item!r}")
            continue

        if " | " in line:
            row = parse_row(line)
            if company is not None:
                role = Role(
                    left=row.left,
                    right=row.right,
                    left_italic=row.left_italic,
                )
                company.roles.append(role)
            elif section is not None:
                close_skill()
                section.blocks.append(row)
            else:
                raise ValueError(f"left/right row outside a section: {line!r}")
            continue

        if skill is not None and not skill.bullets and skill.body is None:
            skill.body = line
        elif section is not None:
            close_company()
            close_skill()
            section.blocks.append(Paragraph(text=line))
        else:
            raise ValueError(f"paragraph outside a section: {line!r}")

    return Resume(name=name, contact=contact, sections=sections)
