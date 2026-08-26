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


def assert_inert(html: str, *, embed_allowed: bool = False) -> None:
    """No tag in the output may carry a handler or a scripting URL.

    `iframe` stays in the forbidden list by default — it is exactly the tag an
    injection would want, and most callers here are adversarial inputs that
    have nothing to do with video. Only a test that renders a real, recognised
    video link passes `embed_allowed=True` (ADR-041): the renderer legitimately
    builds one there, the same reason `button` was never forbidden while
    `button` was the thing being built.
    """
    assert not EVENT_ATTRIBUTE.search(html), f"event handler survived: {html}"
    assert not SCRIPTING_URL.search(html), f"scripting URL survived: {html}"
    tags = ("<script", "<style", "<object", "<embed", "<form", "<svg")
    if not embed_allowed:
        tags += ("<iframe",)
    for tag in tags:
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
        "<pre ",
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


def test_excerpt_of_a_bare_video_is_empty_not_the_buttons_label():
    """T144: falls out of ordinary tag-stripping now — no control label exists
    to leak, so no special case is needed (ADR-041 retired ADR-038's guard)."""
    assert excerpt_from(f"https://youtu.be/{YOUTUBE_ID}") == ""


def test_excerpt_of_a_captioned_video_keeps_the_caption_and_the_prose():
    """Falls out of ordinary tag-stripping now — no special case needed."""
    excerpt = excerpt_from(
        f"[Разбор съёмки](https://youtu.be/{YOUTUBE_ID})\n\nДальше текст статьи."
    )

    assert "Разбор" in excerpt
    assert "Дальше" in excerpt
    assert "Смотреть" not in excerpt


def test_excerpt_of_an_emphasised_caption_holds_no_leftover_tag_text():
    """Review run 9, M-1: an emphasised caption used to leave its markup's own
    tags — escaped, but present — in the excerpt, because the `<iframe>` its
    inline tokens end up inside is opaque to `nh3.clean`'s tag stripping (a
    browser reads an iframe's contents as raw text, never as child elements,
    so the element and the tags inside it both survive as visible text once
    the tag itself is stripped). The caption's own inline tokens are dropped
    from the token stream entirely now (`_figure_paragraphs`), not merely
    hidden by a since-removed special case, so there is nothing left to leak.
    """
    excerpt = excerpt_from(f"[**Разбор**](https://youtu.be/{YOUTUBE_ID})\n\nДальше текст.")

    assert "Разбор" in excerpt
    assert "Дальше" in excerpt
    assert "<" not in excerpt
    assert "&lt;" not in excerpt


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


# -- scrolling boxes --------------------------------------------------------
# Wide content scrolls inside its own box so the page never does. Both boxes
# have to be reachable without a mouse: Chrome 127+ makes scroll containers
# focusable by itself, Firefox and Safari do not.
def test_a_code_block_is_a_focusable_named_region():
    html = render_markdown("```\nprint('привет')\n```")

    assert '<pre tabindex="0" role="region" aria-label="Блок кода">' in html
    assert_inert(html)


def test_a_table_scrolls_in_a_wrapper_and_stays_a_table():
    """`display: block` on a <table> costs it its role and its header links."""
    html = render_markdown("| a | b |\n|---|---|\n| 1 | 2 |")

    assert '<div class="table-scroll" role="region" tabindex="0" aria-label="Таблица">' in html
    assert "<table>" in html
    assert html.count("</div>") == 1, html
    assert "<th>a</th>" in html
    assert_inert(html)


def test_an_author_cannot_write_their_own_region():
    """Raw HTML is off at the parser, so `div` in the allow-list stays ours."""
    html = render_markdown('<div role="region" tabindex="0">взлом</div>')

    assert "<div" not in html, "an author reached the element the renderer owns"
    assert "&lt;div" in html, "it should survive as visible text, escaped"
    assert_inert(html)


# -- intrinsic size ---------------------------------------------------------
# Every picture is `loading="lazy"`, so one that reserves no height lets the
# text below it jump when the bytes land. Two of them measured CLS 0.119
# against a 0.02 budget before `width`/`height` were emitted.
@pytest.fixture
def readable_rendition():
    """A rendition Pillow can actually open, unlike the `renditions` stubs."""
    from PIL import Image

    from app.config import settings

    directory = settings.derived_dir / "post" / "2026"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "picture_1600.webp"
    Image.new("RGB", (1600, 1067), "grey").save(path, "WEBP")
    yield
    path.unlink(missing_ok=True)


def test_a_picture_carries_its_intrinsic_size(readable_rendition):
    html = render_markdown(f"![вершина]({PICTURE}_1600.webp)")

    assert 'width="1600"' in html
    assert 'height="1067"' in html
    assert_inert(html)


def test_a_picture_we_cannot_measure_gets_no_size(renditions):
    """The `renditions` stubs are not decodable: no box beats a guessed box."""
    html = render_markdown(f"![вершина]({PICTURE}_1600.webp)")

    assert "width=" not in html
    assert "height=" not in html


@pytest.mark.parametrize(
    "src",
    [
        "https://evil.example/media/post/2026/picture_1600.webp",
        "/media/../originals/post/2026/picture_1600.webp",
        "/uploads/picture_1600.webp",
    ],
)
def test_a_foreign_url_gets_no_size(src, readable_rendition):
    html = render_markdown(f"![вершина]({src})")

    assert "width=" not in html
    assert "height=" not in html


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


# --------------------------------------------------------------------------
# Video: an iframe the renderer builds directly (F63, ADR-041)
#
# The embed URL reaches the page as an attribute *value*, and nh3 filters
# attribute names only — the same hole `WIDTH_WORDS` closes for the class. So the
# recogniser is a set of anchored per-host patterns, and these are the tests
# that keep it anchored: the only way this module ever emits `iframe.src` is
# with a value `video_embed` returned, never anything else derived from
# author input.
# --------------------------------------------------------------------------
YOUTUBE_ID = "dQw4w9WgXcQ"
RUTUBE_ID = "c0b4c4e2a8f14a1cb0f5e2d3a4b5c6d7"
YOUTUBE_EMBED = f"https://www.youtube.com/embed/{YOUTUBE_ID}"


def embed_of(html: str) -> str | None:
    """The `src` of the rendered `<iframe class="prose-video__frame">`, unescaped."""
    import html as html_module

    found = re.findall(r'<iframe class="prose-video__frame" src="([^"]*)"', html)
    assert len(found) < 2, f"more than one embed: {found}"
    return html_module.unescape(found[0]) if found else None


@pytest.mark.parametrize(
    "url,expected",
    [
        (f"https://www.youtube.com/watch?v={YOUTUBE_ID}", YOUTUBE_EMBED),
        (f"https://youtube.com/watch?v={YOUTUBE_ID}&t=90", YOUTUBE_EMBED),
        (f"https://m.youtube.com/watch?v={YOUTUBE_ID}", YOUTUBE_EMBED),
        (f"https://youtu.be/{YOUTUBE_ID}", YOUTUBE_EMBED),
        (f"https://youtu.be/{YOUTUBE_ID}?t=42", YOUTUBE_EMBED),
        (f"https://www.youtube.com/shorts/{YOUTUBE_ID}", YOUTUBE_EMBED),
        (
            f"https://rutube.ru/video/{RUTUBE_ID}/",
            f"https://rutube.ru/play/embed/{RUTUBE_ID}/",
        ),
        (
            "https://vk.com/video-22822305_456241864",
            "https://vk.com/video_ext.php?oid=-22822305&id=456241864",
        ),
        (
            "https://vkvideo.ru/video-22822305_456241864",
            "https://vk.com/video_ext.php?oid=-22822305&id=456241864",
        ),
    ],
)
def test_a_lone_video_link_becomes_an_embed(url, expected):
    """Every shape the owner might paste, and the embed each one becomes."""
    html = render_markdown(url)

    assert '<figure class="prose-video">' in html
    assert '<iframe class="prose-video__frame"' in html
    assert "<button" not in html
    assert "<a " not in html, "the link became the player, it did not stay beside it"
    assert url not in html, "the pasted address is not printed raw on the page"
    assert embed_of(html) == expected
    assert_inert(html, embed_allowed=True)


def test_the_iframes_src_is_never_anything_but_a_matched_embed_url():
    """The security claim of ADR-041, in one place.

    `iframe` re-entering `ALLOWED_TAGS` is safe only because `link_open`'s
    video branch has exactly one source for `src`: `video_embed`'s return
    value, built from `_VIDEO_SERVICES`'s anchored per-host patterns. A link
    this module does not recognise never reaches that branch at all — it
    stays an ordinary `<a href>` (`test_a_link_to_another_host_stays_an_
    ordinary_link`), never an `<iframe src>` built from the raw address.
    """
    from app.services.markdown import video_embed

    href = f"https://youtu.be/{YOUTUBE_ID}"
    html = render_markdown(href)

    assert embed_of(html) == video_embed(href)
    assert href not in html


@pytest.mark.parametrize(
    "href",
    [
        "https://vimeo.com/76979871",
        "https://dailymotion.com/video/x7tgad0",
        # A host that merely *contains* a supported one.
        f"https://youtube.com.evil.example/watch?v={YOUTUBE_ID}",
        f"https://evil.example/https://youtu.be/{YOUTUBE_ID}",
        f"https://youtu.be.evil.example/{YOUTUBE_ID}",
        # A path the service does not use for a single video.
        f"https://www.youtube.com/playlist?list={YOUTUBE_ID}",
        "https://rutube.ru/video/not-a-hex-id/",
        "https://vk.com/videos-22822305",
        # An identifier that could carry markup, or is not one at all.
        'https://youtu.be/abc"onmouseover=alert(1)',
        "https://youtu.be/ab",
        f"javascript:https://youtu.be/{YOUTUBE_ID}",
        f"https://youtu.be/{YOUTUBE_ID} и ещё слова",
    ],
)
def test_only_a_supported_service_is_recognised(href):
    """Imported inside the test on purpose — T136's lesson: a module-level import
    of a new name makes a pre-change tree fail *collection*, and an ImportError
    proves nothing about the feature."""
    from app.services.markdown import video_embed

    assert video_embed(href) is None


def test_a_link_to_another_host_stays_an_ordinary_link():
    html = render_markdown("https://vimeo.com/76979871")

    assert "prose-video" not in html
    assert '<a href="https://vimeo.com/76979871"' in html
    assert_inert(html)


def test_a_video_link_among_other_text_stays_a_link():
    """The rule pictures already follow: a figure is a paragraph, not a mention."""
    html = render_markdown(f"Смотрите https://youtu.be/{YOUTUBE_ID} сегодня вечером.")

    assert "prose-video" not in html
    assert "<iframe" not in html
    assert f'<a href="https://youtu.be/{YOUTUBE_ID}"' in html


def test_two_video_links_in_one_paragraph_are_not_a_facade():
    html = render_markdown(f"https://youtu.be/{YOUTUBE_ID} https://youtu.be/{YOUTUBE_ID}")

    assert "prose-video" not in html
    assert "<iframe" not in html


def test_a_pictures_caption_survives_the_retired_poster():
    """The poster affordance is retired (ADR-041): the picture never renders,
    but its own alt text still reaches the figure as a caption in place of the
    title it does not have.
    """
    html = render_markdown(f"[![вершина]({PICTURE}_1600.webp)](https://youtu.be/{YOUTUBE_ID})")

    assert '<figure class="prose-video">' in html
    assert f'src="{PICTURE}_1600.webp"' not in html
    assert "<img" not in html
    assert "<figcaption>вершина</figcaption>" in html
    assert embed_of(html) == YOUTUBE_EMBED
    assert "<a " not in html
    assert_inert(html, embed_allowed=True)


def test_a_picture_from_anywhere_else_is_not_a_poster_and_not_a_facade():
    """`img-src 'self' data:` would not load it, and a link is still a link.

    ADR-035 leaves `img-src` alone precisely so that a poster is always this
    site's own file; a foreign one has to stay what the author wrote.
    """
    html = render_markdown(
        f"[![кадр](https://evil.example/thumb.jpg)](https://youtu.be/{YOUTUBE_ID})"
    )

    assert "prose-video" not in html
    assert f'<a href="https://youtu.be/{YOUTUBE_ID}"' in html


def test_the_authors_own_link_text_becomes_the_caption():
    html = render_markdown(f"[Разбор съёмки](https://youtu.be/{YOUTUBE_ID})")

    assert "<figcaption>Разбор съёмки</figcaption>" in html
    assert html.count("Разбор съёмки") == 1, "the words are the caption, not the control's label"
    assert_inert(html, embed_allowed=True)


def test_a_pasted_address_leaves_no_caption():
    """Linkify makes the URL its own link text, and a URL is not a caption."""
    assert "<figcaption" not in render_markdown(f"https://youtu.be/{YOUTUBE_ID}")


def test_a_posters_markdown_title_becomes_the_caption():
    html = render_markdown(
        f'[![вершина]({PICTURE}_1600.webp "Эльбрус на рассвете")](https://youtu.be/{YOUTUBE_ID})'
    )

    assert "<figcaption>Эльбрус на рассвете</figcaption>" in html
    # The picture itself never renders (ADR-041): its own Markdown `title`
    # reaches the figure's caption directly, not as a tooltip on an <img>
    # that no longer exists.
    assert 'title="Эльбрус на рассвете"' not in html


def test_a_handwritten_iframe_does_not_survive_as_an_element():
    """The renderer itself now builds real iframes for recognised video links
    (ADR-041), but an author still cannot type one into existence.

    Raw HTML is off at the parser, so it arrives as text: the tag showing up
    as visible, escaped characters is the neutralisation working, the same
    shape `test_a_handwritten_button_does_not_survive_either` asserts.
    """
    html = render_markdown(
        f'Текст\n\n<iframe src="https://www.youtube.com/embed/{YOUTUBE_ID}"></iframe>\n\nДальше'
    )

    assert "<iframe" not in html
    assert "&lt;iframe" in html
    assert_inert(html)


def test_a_handwritten_button_does_not_survive_either():
    """`button` is not in `ALLOWED_TAGS` at all any more (ADR-041 dropped it),
    but this was never what stopped a hand-typed one from surviving: raw HTML
    is off at the parser, so it arrives as text regardless of what the
    allow-list contains — the attribute name showing up as visible characters
    is the neutralisation working, the same shape `test_onerror_attribute_
    never_becomes_a_tag` asserts for images.
    """
    html = render_markdown('<button data-video="https://evil.example/x">жми</button>')

    assert "<button" not in html
    assert "&lt;button" in html
    assert_inert(html)
