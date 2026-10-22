import pytest

from resume_md.model import BulletList, HorizontalRule, Paragraph
from resume_md.parse import parse_resume

SAMPLE = """\
# Jordan Hale

Austin, TX · (555) 010-2048 · jordan.hale@example.com · github.com/jordanhale

## Profile

Embedded software engineer focused on bootloaders.

## Professional Experience

### Northwind Devices

_Senior Firmware Engineer_ | Jan. 2020 – Present

- Built MCU bootloader

_Firmware Engineer_ | Jun. 2018 – Jan. 2020

- Brought up custom boards

### Contoso Labs

_Software Intern_ | Summer 2017

- Wrote C++ tooling

## Education

**State University - College of Engineering** | Austin, TX

Computer Engineering (BS) | May 2018

GPA: 3.6

## Technical Skills

#### Languages

- C
- C++
- Python

#### Security & Reliability

Secure boot, watchdogs, fault detection
"""


def test_h1_is_name():
    resume = parse_resume(SAMPLE)
    assert resume.name == "Jordan Hale"


def test_contact_splits_on_middle_dot():
    resume = parse_resume(SAMPLE)
    assert resume.contact == [
        "Austin, TX",
        "(555) 010-2048",
        "jordan.hale@example.com",
        "github.com/jordanhale",
    ]


def test_contact_accepts_pipe_separators():
    md = "# Ada Lovelace\n\nLondon | ada@example.com | github.com/ada\n"
    resume = parse_resume(md)
    assert resume.contact == ["London", "ada@example.com", "github.com/ada"]


def test_pipe_row_splits_on_last_pipe():
    md = """\
# Name

City · a@b.c

## Education

**School | College of Engineering** | Austin, TX
"""
    resume = parse_resume(md)
    edu = resume.sections[0]
    row = edu.blocks[0]
    assert row.left == "**School | College of Engineering**"
    assert row.right == "Austin, TX"


def test_nested_company_titles():
    resume = parse_resume(SAMPLE)
    exp = next(s for s in resume.sections if s.title == "Professional Experience")
    northwind = exp.blocks[0]
    assert northwind.name == "Northwind Devices"
    assert len(northwind.roles) == 2
    assert northwind.roles[0].left == "Senior Firmware Engineer"
    assert northwind.roles[0].left_italic is True
    assert northwind.roles[0].right == "Jan. 2020 – Present"
    assert northwind.roles[0].bullets == ["Built MCU bootloader"]
    assert northwind.roles[1].left == "Firmware Engineer"
    assert northwind.roles[1].right == "Jun. 2018 – Jan. 2020"
    contoso = exp.blocks[1]
    assert contoso.name == "Contoso Labs"
    assert contoso.roles[0].left == "Software Intern"


def test_h4_skill_groups_list_and_inline_body():
    resume = parse_resume(SAMPLE)
    skills = next(s for s in resume.sections if s.title == "Technical Skills")
    languages, security = skills.blocks
    assert languages.name == "Languages"
    assert languages.bullets == ["C", "C++", "Python"]
    assert languages.body is None
    assert security.name == "Security & Reliability"
    assert security.bullets == []
    assert security.body == "Secure boot, watchdogs, fault detection"


def test_cpp_not_eaten_in_list_item():
    resume = parse_resume(SAMPLE)
    exp = next(s for s in resume.sections if s.title == "Professional Experience")
    intern_bullets = exp.blocks[1].roles[0].bullets
    assert intern_bullets == ["Wrote C++ tooling"]


def test_thematic_break_is_horizontal_rule():
    md = "# Name\n\nCity · a@b.c\n\n## Profile\n\n---\n\nHello\n"
    resume = parse_resume(md)
    profile = resume.sections[0]
    assert isinstance(profile.blocks[0], HorizontalRule)
    assert isinstance(profile.blocks[1], Paragraph)
    assert profile.blocks[1].text == "Hello"


def test_thematic_break_accepts_asterisks_and_underscores():
    for mark in ("***", "___"):
        md = f"# Name\n\nCity · a@b.c\n\n## Profile\n\n{mark}\n\nHello\n"
        resume = parse_resume(md)
        assert isinstance(resume.sections[0].blocks[0], HorizontalRule)


def test_list_marker_allows_two_or_more_spaces():
    items = {
        "-  two spaces": "two spaces",
        "-   three spaces": "three spaces",
        "-        eight spaces": "eight spaces",
        "-\tone tab": "one tab",
        "- \t mixed": "mixed",
        "*  star": "star",
        "+   plus": "plus",
        "-\u00a0\u00a0nbsp": "nbsp",
    }
    md = "# N\n\nC · a@b.c\n\n## Profile\n\n" + "\n".join(items) + "\n"
    blocks = parse_resume(md).sections[0].blocks
    assert len(blocks) == 1
    assert isinstance(blocks[0], BulletList)
    assert blocks[0].items == list(items.values())


def test_extra_spaces_stay_attached_to_the_role():
    md = """\
# N

C · a@b.c

## Experience

### Acme

_Engineer_ | Jan. 2020 – Present

-  first
-   second
"""
    role = parse_resume(md).sections[0].blocks[0].roles[0]
    assert role.bullets == ["first", "second"]


def test_hyphen_without_following_whitespace_is_not_a_bullet():
    md = "# N\n\nC · a@b.c\n\n## Profile\n\n-not a bullet\n\n10 -  20\n"
    blocks = parse_resume(md).sections[0].blocks
    assert [type(block).__name__ for block in blocks] == ["Paragraph", "Paragraph"]
    assert blocks[0].text == "-not a bullet"
    assert blocks[1].text == "10 -  20"


def test_comments_are_stripped_inline_and_across_lines():
    md = """\
# Jane Doe <!-- draft -->

Example City · jane@example.com <!-- old phone -->

## Profile

<!-- TODO: expand
this note
- not a bullet
-->

A <!-- secret --> mathematician.

- one <!-- drop -->
-  two spaces
"""
    resume = parse_resume(md)
    assert resume.name == "Jane Doe"
    assert resume.contact == ["Example City", "jane@example.com"]
    profile = resume.sections[0]
    assert isinstance(profile.blocks[0], Paragraph)
    assert profile.blocks[0].text == "A mathematician."
    assert isinstance(profile.blocks[1], BulletList)
    assert profile.blocks[1].items == ["one", "two spaces"]


def test_multiline_comment_does_not_swallow_the_next_section():
    md = """\
# Jane

City · a@b.c

## One

<!--
## Hidden
-->

## Two

Visible
"""
    resume = parse_resume(md)
    assert [section.title for section in resume.sections] == ["One", "Two"]
    assert resume.sections[1].blocks[0].text == "Visible"


def test_crlf_comment_is_stripped():
    md = "# Jane\r\n\r\nCity · a@b.c\r\n\r\n## Profile\r\n\r\n<!--\r\nTODO\r\n-->\r\n\r\nHello\r\n"
    resume = parse_resume(md)
    assert resume.sections[0].blocks[0].text == "Hello"


def test_unclosed_comment_names_the_line():
    md = "# Jane\n\nCity · a@b.c\n\n<!-- never closed\n"
    with pytest.raises(ValueError, match=r"unclosed HTML comment on line 5"):
        parse_resume(md)


def test_front_matter_font_and_section_rule():
    md = """\
---
# chosen face
font: "Example Sans", sans-serif
---

# Jane

City · a@b.c

## Profile

---

Hello
"""
    resume = parse_resume(md)
    assert resume.font == '"Example Sans", sans-serif'
    assert resume.name == "Jane"
    assert isinstance(resume.sections[0].blocks[0], HorizontalRule)
    assert resume.sections[0].blocks[1].text == "Hello"


def test_empty_front_matter_leaves_font_unset():
    resume = parse_resume("---\n---\n# Jane\n\nCity · a@b.c\n")
    assert resume.font is None
    assert resume.name == "Jane"


def test_front_matter_rejects_unknown_duplicate_and_unclosed():
    with pytest.raises(ValueError, match="unknown front matter key 'name'"):
        parse_resume("---\nname: Jane\n---\n# Jane\n\nCity · a@b.c\n")
    with pytest.raises(ValueError, match="set more than once"):
        parse_resume("---\nfont: Georgia\nfont: Cambria\n---\n# Jane\n\nCity · a@b.c\n")
    with pytest.raises(ValueError, match="unclosed front matter"):
        parse_resume("---\nfont: Georgia\n# Jane\n\nCity · a@b.c\n")
    with pytest.raises(ValueError, match="font is empty"):
        parse_resume("---\nfont:\n---\n# Jane\n\nCity · a@b.c\n")
