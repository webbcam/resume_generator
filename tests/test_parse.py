from resume_md.model import HorizontalRule, Paragraph
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
