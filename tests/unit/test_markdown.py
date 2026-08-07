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


# --------------------------------------------------------------------------
# Pictures: width, caption, srcset (F9)
#
# The size vocabulary reaches the renderer as an arbitrary class value, and
# nh3 filters attribute *names* only. So the closed list is enforced in
# `app.services.markdown` before the sanitiser runs, and these are the tests
# that keep it closed.
# --------------------------------------------------------------------------
PICTURE = "/media/post/2026/picture"


@pytest.fixture
def renditions():
    """Two real renditions on disk, so `srcset` has something to find."""
    from app.config import settings

    directory = settings.derived_dir / "post" / "2026"
    directory.mkdir(parents=True, exist_ok=True)
    written = [directory / f"picture_{width}.webp" for width in (640, 1600)]
    for path in written:
        path.write_bytes(b"not really a webp, but it exists")
    yield
    for path in written:
        path.unlink(missing_ok=True)


# -- width ------------------------------------------------------------------
def test_a_lone_image_becomes_a_figure_at_the_text_width():
    html = render_markdown(f"![вершина]({PICTURE}_1600.webp)")

    assert '<figure class="prose-figure">' in html
    assert "prose-figure--" not in html, "no modifier without one in the source"
    assert "<figcaption" not in html, "no title in the source, so no caption"
    assert_inert(html)


@pytest.mark.parametrize("word", ["wide", "full"])
def test_each_width_word_reaches_the_figure(word):
    html = render_markdown(f"![вершина]({PICTURE}_1600.webp){{.{word}}}")

    assert f'<figure class="prose-figure prose-figure--{word}">' in html
    assert_inert(html)


@pytest.mark.parametrize("word", ["huge", "wide-ish", "prose-figure--full", "sidebar"])
def test_an_unknown_width_word_is_dropped(word):
    html = render_markdown(f"![вершина]({PICTURE}_1600.webp){{.{word}}}")

    assert '<figure class="prose-figure">' in html
    assert word not in html, f"{word!r} reached the page"
    assert_inert(html)


# -- caption ----------------------------------------------------------------
def test_the_markdown_title_becomes_the_caption():
    html = render_markdown(f'![вершина]({PICTURE}_1600.webp "Эльбрус на рассвете")')

    assert "<figcaption>Эльбрус на рассвете</figcaption>" in html
    assert 'alt="вершина"' in html, "the caption does not replace the alt text"
    assert "title=" not in html, "the title is the caption now, not a tooltip too"


def test_a_caption_cannot_smuggle_markup():
    html = render_markdown(f'![вершина]({PICTURE}_1600.webp "<script>alert(1)</script>")')

    assert "<script" not in html
    assert_inert(html)


# -- figure or inline -------------------------------------------------------
def test_an_image_among_text_stays_a_bare_img():
    """No figure, and no width either: inline there is nothing to break out of."""
    html = render_markdown(f"Смотрите ![вершина]({PICTURE}_1600.webp){{.wide}} — вот она.")

    assert "<figure" not in html
    assert "<p>" in html
    assert "<img " in html
    assert "class=" not in html


def test_two_images_in_one_paragraph_are_not_a_figure():
    html = render_markdown(f"![один]({PICTURE}_640.webp)\n![два]({PICTURE}_1600.webp)")

    assert "<figure" not in html
    assert html.count("<img") == 2


def test_an_image_in_a_list_item_is_not_a_figure():
    html = render_markdown(f"- ![вершина]({PICTURE}_1600.webp)")

    assert "<figure" not in html
    assert "<li>" in html


# -- srcset -----------------------------------------------------------------
def test_srcset_lists_the_renditions_that_exist(renditions):
    html = render_markdown(f"![вершина]({PICTURE}_1600.webp)")

    assert f'srcset="{PICTURE}_640.webp 640w, {PICTURE}_1600.webp 1600w"' in html
    assert "sizes=" in html
    assert 'loading="lazy"' in html
    assert 'decoding="async"' in html


def test_sizes_follows_the_width_word(renditions):
    narrow = render_markdown(f"![вершина]({PICTURE}_1600.webp)")
    full = render_markdown(f"![вершина]({PICTURE}_1600.webp){{.full}}")

    assert re.search(r'sizes="[^"]+"', narrow)
    assert re.search(r'sizes="[^"]+"', full)
    assert re.search(r'sizes="([^"]+)"', narrow)[1] != re.search(r'sizes="([^"]+)"', full)[1]


@pytest.mark.parametrize(
    "src",
    [
        "/media/post/2026/nothing-on-disk_1600.webp",
        "https://evil.example/media/post/2026/picture_1600.webp",
        "/media/../../../etc/passwd_640.webp",
        "/media/post/2026/picture_1600.webp?resize=1",
        "/uploads/picture_1600.webp",
        "/media/post/2026/picture.webp",
    ],
)
def test_a_foreign_url_gets_no_srcset(src, renditions):
    html = render_markdown(f"![вершина]({src})")

    assert "srcset" not in html, f"{src} must render as a plain <img>"
    assert "sizes=" not in html
    assert "<img" in html
    assert_inert(html)


def test_srcset_never_escapes_the_media_root(renditions):
    """A crafted stem must not be able to name a file outside `derived/`."""
    html = render_markdown("![вершина](/media/../originals/post/2026/picture_1600.webp)")

    assert "srcset" not in html, "a path out of the media root produced renditions"
    assert_inert(html)


# -- smuggling --------------------------------------------------------------
@pytest.mark.parametrize(
    "attrs",
    [
        '{style="position:fixed;inset:0"}',
        "{onerror=alert(1)}",
        "{.wide onclick=alert(1)}",
        '{.wide onclick="alert(1)"}',
        '{.wide style="display:none"}',
        '{class="wide" onload="alert(1)"}',
        "{srcset=x}",
        '{alt="x" title="y"}',
    ],
)
def test_curly_attributes_can_only_ever_carry_a_width(attrs):
    html = render_markdown(f"![вершина]({PICTURE}_1600.webp){attrs}")

    # `assert_inert` already proves no tag carries a handler; what is left to
    # show is that the one attribute we do allow says only what we chose.
    assert_inert(html)
    assert "style=" not in html
    for surviving in re.findall(r'class="([^"]*)"', html):
        for name in surviving.split():
            assert name in {"prose-figure", "prose-figure--wide", "prose-figure--full"}, (
                f"unexpected class {name!r} from {attrs}"
            )


def test_a_javascript_url_with_a_width_is_still_refused():
    html = render_markdown("![вершина](javascript:alert(1)){.wide}")

    assert "<img" not in html
    assert_inert(html)


def test_a_width_on_something_that_is_not_an_image_is_literal_text():
    """`attrs` is wired to images only, so nothing else can grow a class."""
    html = render_markdown("## Заголовок {.wide}\n\nАбзац `код`{.wide} дальше.\n")

    assert "class=" not in html
    assert "{.wide}" in html, "left as text rather than silently swallowed"
