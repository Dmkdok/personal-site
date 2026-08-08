"""Markdown → sanitised HTML.

Shared by the blog, project descriptions and editable site copy, so the preview
in the editor and the published page can never diverge: they call this.

Raw HTML is disabled at the parser level *and* the output is passed through an
allow-list sanitiser. Either alone would probably do; both is cheap.

On top of CommonMark, pictures get three things, all of them written in the
Markdown source so the owner never has to touch HTML:

* a width — `![описание](url){.wide}` and `{.full}`, see `WIDTH_WORDS`;
* a caption — a paragraph holding nothing but an image becomes a `<figure>`,
  and the image's Markdown title becomes its `<figcaption>`;
* a `srcset`, derived from the renditions that are actually on disk.

`{...}` is parsed by `attrs_plugin`, restricted to images and to the single
attribute `class`. The *value* of that class is still whatever the author
typed, and nh3 cannot filter attribute values — only names. So the vocabulary
is closed here, in the renderer, before the sanitiser ever sees the markup:
anything outside `WIDTH_WORDS` is silently dropped.
"""

import re
from typing import Any

import nh3
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from mdit_py_plugins.attrs import attrs_plugin

# `renditions_of` is app.services.images' own glob over a stem's renditions.
# Importing it rather than writing a second one is deliberate: it applies the
# containment check that guards every other media path, so a crafted `src`
# pointing outside the media root simply finds nothing.
from app.services.images import intrinsic_size, media_url, renditions_of

#: The words an author may write inside `{...}` after an image. Everything else
#: is dropped, so a class attribute can never carry anything we did not choose.
WIDTH_WORDS: tuple[str, ...] = ("wide", "full")

#: How much of the viewport each width ends up occupying, mirroring the three
#: rules in prose.css. Only a hint to the browser, but a wrong one costs bytes.
_SIZES: dict[str | None, str] = {
    None: "(max-width: 46rem) 100vw, 40rem",
    "wide": "(max-width: 63rem) 100vw, 59rem",
    "full": "(max-width: 80rem) 100vw, 76rem",
}

_MEDIA_PREFIX = "/media/"

#: Openers for the two scrolling boxes in prose. `role="region"` gives the box
#: a name once it is focusable, so a screen reader says what has just been
#: entered instead of announcing a bare group.
_PRE_OPEN = '<pre tabindex="0" role="region" aria-label="Блок кода">'
_TABLE_SCROLL_OPEN = '<div class="table-scroll" role="region" tabindex="0" aria-label="Таблица">'

#: `<stem>_<width>.webp`, the shape app.services.images gives every rendition.
#: The stem is matched, never assumed: the directory layout under the media
#: root is free to change without touching this module.
_RENDITION = re.compile(r"^(?P<stem>[^?#]+)_(?P<width>\d{2,5})\.webp$")


def _width_word(token: Token) -> str | None:
    """The one recognised word from `{.wide}` / `{.full}`, or None."""
    for word in (token.attrGet("class") or "").split():
        if word in WIDTH_WORDS:
            return word
    return None


def _srcset(src: str) -> str:
    """`srcset` over the sibling renditions of `src` that exist on disk.

    Empty for anything that is not one of our own `/media/<stem>_<width>.webp`
    files — a hand-written or foreign URL renders as a plain `<img>` rather
    than as a promise of renditions nobody generated.

    The siblings are found by glob rather than by walking a width tuple: an
    upload's ladder depends on the profile it came in under and on whether it
    was deduplicated onto another one's files, so the tuple in force today is
    not an answer to what is on disk.
    """
    if not src.startswith(_MEDIA_PREFIX):
        return ""
    match = _RENDITION.match(src[len(_MEDIA_PREFIX) :])
    if not match:
        return ""

    found = sorted(renditions_of(match["stem"]).items())

    # One rendition is not a choice; saying so only inflates the markup.
    if len(found) < 2:
        return ""
    return ", ".join(f"{media_url(relative)} {width}w" for width, relative in found)


def _dimensions(src: str) -> tuple[int, int] | None:
    """The pixel size of the rendition `src` points at, or None.

    Every picture in an article is `loading="lazy"`, so until its bytes arrive
    it occupies no height and the text below it sits too high; when it lands,
    that text jumps. Two pictures were enough to score CLS 0.119 against this
    project's 0.02 budget. `width`/`height` give the browser the ratio to
    reserve the box up front — the intrinsic size, not the displayed one, which
    prose.css still governs through `inline-size: 100%`.

    Foreign URLs get nothing: their size is unknowable here, and a guess would
    reserve the wrong box, which is worse than reserving none.
    """
    if not src.startswith(_MEDIA_PREFIX):
        return None
    return intrinsic_size(src[len(_MEDIA_PREFIX) :])


def _figure_paragraphs(state: Any) -> None:
    """Mark every paragraph that holds nothing but one image.

    Those become `<figure>`; an image sitting among other text stays a bare
    `<img>`. Run as a core rule because a paragraph's contents are the one
    thing the inline image renderer cannot see from where it stands.
    """
    tokens = state.tokens
    for index, opening in enumerate(tokens):
        if opening.type != "paragraph_open" or opening.hidden:
            # `hidden` is a tight list item: it has no <p> to replace.
            continue
        if index + 2 >= len(tokens):
            continue
        inline, closing = tokens[index + 1], tokens[index + 2]
        if inline.type != "inline" or closing.type != "paragraph_close":
            continue

        children = [
            child
            for child in (inline.children or [])
            if child.type != "text" or child.content.strip()
        ]
        if len(children) != 1 or children[0].type != "image":
            continue

        image = children[0]
        image.meta["in_figure"] = True
        opening.meta["figure_image"] = image
        closing.meta["figure_image"] = image


class _ProseRenderer(RendererHTML):
    """Renders the picture vocabulary above; everything else is CommonMark."""

    def image(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        token = tokens[idx]
        src = token.attrGet("src") or ""
        alt = self.renderInlineAsText(token.children or [], options, env)
        in_figure = bool(token.meta.get("in_figure"))

        # The width belongs to the <figure>. An image set among words has
        # nothing to break out of, so `{.wide}` there is simply ignored — no
        # class, and the ordinary `sizes`.
        width = _width_word(token) if in_figure else None

        # `src` first, then `alt`: the order the default renderer used, and the
        # order the sanitiser and the tests have always seen.
        parts = [f'src="{escapeHtml(src)}"', f'alt="{escapeHtml(alt)}"']

        title = token.attrGet("title")
        if title and not in_figure:
            # Inside a figure the title is the caption, not a second tooltip.
            parts.append(f'title="{escapeHtml(title)}"')

        pixels = _dimensions(src)
        if pixels:
            parts += [f'width="{pixels[0]}"', f'height="{pixels[1]}"']

        srcset = _srcset(src)
        if srcset:
            parts.append(f'srcset="{escapeHtml(srcset)}"')
            parts.append(f'sizes="{escapeHtml(_SIZES[width])}"')

        parts += ['loading="lazy"', 'decoding="async"']
        return "<img " + " ".join(parts) + " />"

    def paragraph_open(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        image = tokens[idx].meta.get("figure_image")
        if image is None:
            return self.renderToken(tokens, idx, options, env)

        classes = "prose-figure"
        width = _width_word(image)
        if width:
            classes += f" prose-figure--{width}"
        return f'<figure class="{classes}">\n'

    # A scrolling box has to be reachable without a mouse. Chrome 127+ makes
    # scroll containers focusable on its own; Firefox and Safari do not, and
    # there a wide code block or table simply cannot be read from a keyboard.
    def fence(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        return super().fence(tokens, idx, options, env).replace("<pre>", _PRE_OPEN, 1)

    def code_block(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        return super().code_block(tokens, idx, options, env).replace("<pre>", _PRE_OPEN, 1)

    def table_open(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        # The scroller is this wrapper, never the table: `display: block` on a
        # <table> costs it its role, its header associations and its row and
        # column counts in the accessibility tree.
        return f"{_TABLE_SCROLL_OPEN}<table>"

    def table_close(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        return "</table></div>\n"

    def paragraph_close(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        image = tokens[idx].meta.get("figure_image")
        if image is None:
            return self.renderToken(tokens, idx, options, env)

        caption = image.attrGet("title") or ""
        if not caption:
            return "\n</figure>\n"
        return f"\n<figcaption>{escapeHtml(caption)}</figcaption>\n</figure>\n"


_md = MarkdownIt(
    "commonmark", {"html": False, "linkify": True, "typographer": True}, renderer_cls=_ProseRenderer
).enable(["table", "strikethrough", "linkify", "replacements", "smartquotes"])
# Images only, `class` only: a heading or a link cannot pick up an attribute,
# and no attribute but `class` survives the parser.
_md.use(attrs_plugin, after=("image",), allowed=["class"])
_md.core.ruler.push("prose_figures", _figure_paragraphs)

# fmt: off
# Grouped by role — block, headings, inline, lists, media, table — because the
# allow-list is read when auditing what survives sanitising. One tag per line
# would be 30 lines of noise and lose the grouping.
ALLOWED_TAGS: set[str] = {
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "s", "del", "code", "pre", "kbd", "sup", "sub",
    "blockquote", "ul", "ol", "li",
    "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div",
}
# fmt: on

ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    # No "rel" here: nh3 rejects it in the allow-list when link_rel is set, and
    # sets rel="noopener noreferrer" on every link itself.
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height", "loading", "decoding", "srcset", "sizes"},
    # "class" only on the one element that carries a width, and safe there only
    # because the renderer above has already reduced it to WIDTH_WORDS — nh3
    # filters attribute names, never values. "style" is never allowed: the CSP
    # forbids it, and it would be a way out of the layout.
    "figure": {"class"},
    # The two scrolling boxes. Authors cannot produce either set of attributes:
    # raw HTML is off at the parser and `attrs_plugin` reaches images only, so
    # these arrive from the renderer above or not at all.
    "div": {"class", "role", "tabindex", "aria-label"},
    "pre": {"role", "tabindex", "aria-label"},
    "td": {"align"},
    "th": {"align", "scope"},
    "code": {"class"},
    "span": {"class"},
}

ALLOWED_URL_SCHEMES: set[str] = {"http", "https", "mailto", "tel"}


def render_markdown(text: str) -> str:
    """Render Markdown to HTML that is safe to insert into a page."""
    if not text:
        return ""
    raw = _md.render(text)
    return nh3.clean(
        raw,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )


def render_inline(text: str) -> str:
    """Render a single paragraph's worth of Markdown without wrapping it in <p>."""
    if not text:
        return ""
    raw = _md.renderInline(text)
    return nh3.clean(
        raw,
        tags=ALLOWED_TAGS - {"p", "div"},
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )


def excerpt_from(text: str, limit: int = 220) -> str:
    """Plain-text summary for cards and meta descriptions."""
    plain = nh3.clean(_md.render(text or ""), tags=set(), attributes={}).strip()
    plain = " ".join(plain.split())
    if len(plain) <= limit:
        return plain
    return plain[:limit].rsplit(" ", 1)[0].rstrip(",.;:—-") + "…"
