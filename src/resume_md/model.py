from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Role:
    left: str
    right: str
    left_italic: bool
    bullets: list[str] = field(default_factory=list)


@dataclass
class Company:
    name: str
    roles: list[Role] = field(default_factory=list)


@dataclass
class SkillGroup:
    name: str
    bullets: list[str] = field(default_factory=list)
    body: str | None = None


@dataclass
class Row:
    left: str
    right: str
    left_italic: bool = False


@dataclass
class Paragraph:
    text: str


@dataclass
class BulletList:
    items: list[str]


@dataclass
class HorizontalRule:
    pass


Block = Company | SkillGroup | Row | Paragraph | BulletList | HorizontalRule


@dataclass
class Section:
    title: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Resume:
    name: str
    contact: list[str]
    sections: list[Section] = field(default_factory=list)
