"""Markdown rendering and sanitisation (F31).

The blog stores `body_html` once, at write time, and serves it with `|safe`.
Everything that keeps that safe is in `app.services.markdown`, so these are the
tests that stand between an article body and stored XSS.
"""

import re

import pytest

from app.services.markdown import excerpt_from, render_inline, render_markdown

# Anything that would run: an event handler on a tag, or a scripting URL.
EVENT_ATTRIBUTE = re.compile(r"<[^>]*\son[a-z]+\s*=", re.IGNORECASE)
SCRIPTING_URL = re.compile(r"(href|src)\s*=\s*[\"']?\s*(javascript|data|vbscript):", re.IGNORECASE)


def assert_inert(html: str) -> None:
    """No tag in the output may carry a handler or a scripting URL."""
    assert not EVENT_ATTRIBUTE.search(html), f"event handler survived: {html}"
    assert not SCRIPTING_URL.search(html), f"scripting URL survived: {html}"
    for tag in ("<script", "<style", "<iframe", "<object", "<embed", "<form", "<svg"):
        assert tag not in html.lower(), f"{tag} survived: {html}"


# --------------------------------------------------------------------------
# Sanitisation
# --------------------------------------------------------------------------
def test_script_tag_is_stripped():
    html = render_markdown("Перед\n\n<script>alert('xss')</script>\n\nПосле")

    assert "<script" not in html
    assert "alert" in html, "the text may stay; only the tag must not"
    assert_inert(html)


def test_onerror_attribute_never_becomes_a_tag():
    html = render_markdown('<img src="x" onerror="alert(1)">')

    # Raw HTML is neutralised into text, so nothing is left to fire.
    assert "<img" not in html
    assert "&lt;img" in html
    assert_inert(html)


@pytest.mark.parametrize(
    "source",
    [
        "[кликни](javascript:alert(1))",
        "[кликни](JaVaScRiPt:alert(1))",
        "![картинка](javascript:alert(1))",
        '<a href="javascript:alert(1)">кликни</a>',
    ],
)
def test_javascript_urls_never_reach_an_attribute(source):
    assert_inert(render_markdown(source))


@pytest.mark.parametrize(
    "source",
    [
        '<div onclick="steal()">блок</div>',
        '<iframe src="https://evil.example"></iframe>',
        "<style>body{display:none}</style>",
        '<svg><use href="#x" /></svg>',
        '<form action="https://evil.example"><input name="p"></form>',
    ],
)
def test_raw_html_is_stripped(source):
    html = render_markdown(source)

    assert_inert(html)
    assert "&lt;" in html, "the markup should be shown as text, not silently vanish"


def test_link_gets_a_safe_rel():
    html = render_markdown("[сайт](https://example.com)")

    assert 'href="https://example.com"' in html
    assert 'rel="noopener noreferrer"' in html


def test_inline_rendering_is_sanitised_too():
    html = render_inline("обычный **текст** <img src=x onerror=alert(1)>")

    assert "<strong>текст</strong>" in html
    assert "<p>" not in html
    assert_inert(html)


def test_empty_input_renders_nothing():
    assert render_markdown("") == ""
    assert render_inline("") == ""


# --------------------------------------------------------------------------
# Ordinary formatting must survive
# --------------------------------------------------------------------------
def test_common_formatting_is_preserved():
    html = render_markdown(
        "## Подзаголовок\n"
        "\n"
        "Абзац с **жирным**, _курсивом_, ~~зачёркнутым~~ и `кодом`.\n"
        "\n"
        "- первый\n"
        "- второй\n"
        "\n"
        "1. раз\n"
        "2. два\n"
        "\n"
        "> Цитата\n"
        "\n"
        "```\n"
        "print('привет')\n"
        "```\n"
        "\n"
        "![вершина](/media/post/2026/a_1600.webp)\n"
        "\n"
        "[ссылка](https://example.com)\n"
    )

    for fragment in (
        "<h2>Подзаголовок</h2>",
        "<strong>жирным</strong>",
        "<em>курсивом</em>",
        "<code>кодом</code>",
        "<ul>",
        "<ol>",
        "<blockquote>",
        "<pre>",
        '<img src="/media/post/2026/a_1600.webp" alt="вершина"',
        '<a href="https://example.com"',
    ):
        assert fragment in html, f"lost {fragment}"

    assert "<s>зачёркнутым</s>" in html or "<del>зачёркнутым</del>" in html


def test_tables_survive():
    html = render_markdown("| Гора | Высота |\n| --- | --- |\n| Эльбрус | 5642 |\n")

    assert "<table>" in html
    assert "<th>Гора</th>" in html
    assert "<td>Эльбрус</td>" in html


# --------------------------------------------------------------------------
# Excerpts
# --------------------------------------------------------------------------
def test_excerpt_is_plain_text():
    excerpt = excerpt_from("## Заголовок\n\nПервый **абзац** с [ссылкой](https://example.com).")

    assert "<" not in excerpt
    assert "Заголовок" in excerpt
    assert "абзац" in excerpt


def test_excerpt_is_capped_and_ends_on_a_word():
    excerpt = excerpt_from("слово " * 200, limit=60)

    assert len(excerpt) <= 61  # the ellipsis is added after the cut
    assert excerpt.endswith("…")


def test_excerpt_of_nothing_is_empty():
    assert excerpt_from("") == ""
