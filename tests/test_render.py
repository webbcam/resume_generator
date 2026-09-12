from pathlib import Path

from resume_md.parse import parse_resume
from resume_md.render import markdown_to_html, render_html

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_MD = ROOT / "examples" / "sample.md"
GOLDEN = Path(__file__).resolve().parent / "golden" / "sample.html"


def test_contact_joined_with_diamonds():
    html = markdown_to_html(
        "# Ada Lovelace\n\nLondon · ada@example.com · github.com/ada\n"
    )
    assert "London ◆ ada@example.com ◆ github.com/ada" in html
    assert " · " not in html.split("<body", 1)[-1]


def test_role_row_is_left_italic_and_right_date():
    html = markdown_to_html(
        "# N\n\nC · e@x.c\n\n## Experience\n\n### Acme\n\n_Engineer_ | Jan. 2020 – Present\n"
    )
    assert 'class="left italic"' in html
    assert "Engineer" in html
    assert "Jan. 2020 – Present" in html
    assert "<em>" not in html or "Engineer" in html


def test_skill_h4_and_cpp_preserved():
    html = markdown_to_html(SAMPLE_MD.read_text(encoding="utf-8"))
    assert "<h4>Languages</h4>" in html
    assert "<li>C++</li>" in html
    assert "C++ tooling" in html
    assert "<h4>Security &amp; Reliability</h4>" in html
    assert "Secure boot, watchdogs, fault detection" in html


def test_education_bold_left_and_gpa_paragraph():
    html = markdown_to_html(SAMPLE_MD.read_text(encoding="utf-8"))
    assert "<strong>State University - College of Engineering</strong>" in html
    assert "Austin, TX" in html
    assert "Computer Engineering (BS)" in html
    assert "GPA: 3.6" in html


def test_section_heads_are_h2_without_underline_class():
    html = markdown_to_html(SAMPLE_MD.read_text(encoding="utf-8"))
    assert "<h2>Profile</h2>" in html
    assert "<h2>Professional Experience</h2>" in html
    assert "text-decoration: underline" not in html


def test_section_heads_do_not_have_automatic_bottom_rule():
    html = markdown_to_html("# N\n\nC · e@x.c\n\n## Profile\n\nHello\n")
    assert "<h2>Profile</h2>" in html
    assert "<hr>" not in html
    assert "border-bottom: 0.75pt solid #000" not in html
    assert "border-bottom: none" in html


def test_thematic_break_renders_as_hr():
    html = markdown_to_html("# N\n\nC · e@x.c\n\n## Profile\n\n---\n\nHello\n")
    assert "<hr>" in html
    assert "Hello" in html


def test_stylesheet_uses_cambria_stack():
    html = render_html(parse_resume("# N\n\nC · e@x.c\n"))
    assert 'font-family: Cambria, Palatino, "Palatino Linotype", Georgia, serif' in html
    assert "24pt" in html
    assert "@page" in html
    assert "letter" in html


def test_golden_html_snapshot(request):
    html = markdown_to_html(SAMPLE_MD.read_text(encoding="utf-8"))
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    if request.config.getoption("--update-golden"):
        GOLDEN.write_text(html, encoding="utf-8")
    expected = GOLDEN.read_text(encoding="utf-8")
    assert html == expected
