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

A video gets the same treatment one level up (F63, ADR-035): a paragraph holding
nothing but a link to one of the services in `_VIDEO_SERVICES` becomes a
`<figure class="prose-video">` around a `<button>` carrying the embed URL, and
`video.js` builds the `<iframe>` when a reader presses it. `iframe` is not in
`ALLOWED_TAGS`, so nothing that comes through here can embed anything; the URL in
the button is built from an anchored per-host pattern for the same reason
`WIDTH_WORDS` exists.
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
from app.templating import translate

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

#: The characters a video service's own identifiers are made of. Deliberately
#: narrow: the matched value ends up inside `data-video`, and a class that cannot
#: hold a quote, a space, a colon or an angle bracket is what makes that
#: attribute closed by this module rather than by the author.
_VIDEO_ID = r"[A-Za-z0-9_-]{6,24}"

#: Query and fragment the author's URL may carry and this module throws away —
#: `&t=90`, `?si=…`, `#`. Matched so the link is still recognised, never used.
_VIDEO_TAIL = r"(?:[?&#]\S*)?"

#: The three services the owner asked for (F63, ADR-035), each as an **anchored
#: pattern per host** and the embed URL it becomes. Never a general URL parse:
#: nh3 filters attribute names and never values, so the URL in `data-video` has
#: to be built here from groups this module constrained — exactly the reason
#: `WIDTH_WORDS` exists for the class attribute. `autoplay=1` is part of the
#: embed because the reader has already pressed play once by then.
_VIDEO_SERVICES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            rf"https?://(?:www\.|m\.)?youtube\.com/watch\?v=(?P<id>{_VIDEO_ID}){_VIDEO_TAIL}"
        ),
        "https://www.youtube.com/embed/{id}?autoplay=1",
    ),
    (
        re.compile(rf"https?://youtu\.be/(?P<id>{_VIDEO_ID}){_VIDEO_TAIL}"),
        "https://www.youtube.com/embed/{id}?autoplay=1",
    ),
    (
        re.compile(rf"https?://(?:www\.)?youtube\.com/shorts/(?P<id>{_VIDEO_ID}){_VIDEO_TAIL}"),
        "https://www.youtube.com/embed/{id}?autoplay=1",
    ),
    (
        re.compile(rf"https?://rutube\.ru/video/(?P<id>[0-9a-f]{{32}})/?{_VIDEO_TAIL}"),
        "https://rutube.ru/play/embed/{id}/?autoplay=1",
    ),
    (
        re.compile(
            r"https?://(?:m\.)?(?:vk\.com|vkvideo\.ru)/video(?P<oid>-?\d{1,20})_(?P<id>\d{1,20})"
            + _VIDEO_TAIL
        ),
        "https://vk.com/video_ext.php?oid={oid}&id={id}&autoplay=1",
    ),
)


def video_embed(href: str) -> str | None:
    """The embed URL for a link to a supported video service, or None.

    `fullmatch`, so a host that merely *contains* one of these — say
    `youtube.com.evil.example/watch?v=x` — is not a video link, and neither is a
    link to anywhere else. A `None` here is what keeps every other link an
    ordinary link.
    """
    for pattern, embed in _VIDEO_SERVICES:
        match = pattern.fullmatch(href.strip())
        if match:
            return embed.format(**match.groupdict())
    return None


#: Openers for the two scrolling boxes in prose. `role="region"` gives the box
#: a name once it is focusable, so a screen reader says what has just been
#: entered instead of announcing a bare group.
#:
#: Built per call rather than held as constants: the name is a user-visible
#: string and therefore lives in the catalogue (ADR-007), and the catalogue is
#: loaded on import — reading it at import time here would depend on which
#: module got there first.


def _pre_open() -> str:
    label = escapeHtml(translate("prose.code_block"))
    return f'<pre tabindex="0" role="region" aria-label="{label}">'


def _table_scroll_open() -> str:
    label = escapeHtml(translate("prose.table"))
    return f'<div class="table-scroll" role="region" tabindex="0" aria-label="{label}">'


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


def _video_paragraph(children: list[Token]) -> tuple[str, Token | None, str] | None:
    """`(embed URL, poster image or None, caption)` for a paragraph of one video link.

    The same shape this module already recognises for a picture: the link has to
    be the whole paragraph. A video link **among other text** stays an ordinary
    link, which is the rule pictures follow too.

    A picture from this site's own media inside the link becomes the poster. A
    picture from anywhere else makes it not a video paragraph at all — `img-src
    'self' data:` would not load a foreign poster (ADR-035 leaves that directive
    alone), and a link wrapping a foreign picture is still a perfectly good link.
    """
    if len(children) < 2 or children[0].type != "link_open" or children[-1].type != "link_close":
        return None
    href = children[0].attrGet("href") or ""
    embed = video_embed(href)
    if embed is None:
        return None

    inside = children[1:-1]
    # The paragraph's first `link_open` must be closed by its last `link_close`.
    # Without this, «link link» in one paragraph looks like one link wrapping
    # another link's boundaries, and two mentions would become one player.
    if any(child.type in ("link_open", "link_close") for child in inside):
        return None

    pictures = [child for child in inside if child.type == "image"]
    words = "".join(child.content for child in inside if child.type == "text").strip()

    # A linkified or autolinked address is its own link text, and that is a URL,
    # not a caption. Anything the author typed themselves is one, so their words
    # are kept instead of being swallowed by the button that replaces the link.
    linkified = children[0].markup in ("linkify", "autolink")
    caption = "" if linkified or words == href else words

    if not pictures:
        return embed, None, caption
    if len(pictures) != 1 or len(inside) != 1:
        return None
    src = pictures[0].attrGet("src") or ""
    if not src.startswith(_MEDIA_PREFIX):
        return None
    return embed, pictures[0], caption


def _figure_paragraphs(state: Any) -> None:
    """Mark every paragraph that holds nothing but one image, or one video link.

    Those become `<figure>`; an image or a video link sitting among other text
    stays what it was. Run as a core rule because a paragraph's contents are the
    one thing the inline renderers cannot see from where they stand.
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
        if len(children) == 1 and children[0].type == "image":
            image = children[0]
            image.meta["in_figure"] = True
            opening.meta["figure_image"] = image
            closing.meta["figure_image"] = image
            continue

        video = _video_paragraph(children)
        if video is None:
            continue

        embed, poster, caption = video
        opening.meta["figure_video"] = embed
        closing.meta["figure_video"] = embed
        closing.meta["figure_caption"] = caption or (
            poster.attrGet("title") if poster is not None else ""
        )
        # The link becomes the button, and everything the link held becomes the
        # button's contents — except its text, which is a URL or a caption and in
        # neither case something to print inside a control.
        children[0].meta["video_embed"] = embed
        children[-1].meta["video_embed"] = embed
        for child in children[1:-1]:
            if child.type == "text":
                child.meta["video_text"] = True
        if poster is not None:
            poster.meta["in_figure"] = True


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
        if tokens[idx].meta.get("figure_video"):
            return '<figure class="prose-video">\n'

        image = tokens[idx].meta.get("figure_image")
        if image is None:
            return self.renderToken(tokens, idx, options, env)

        classes = "prose-figure"
        width = _width_word(image)
        if width:
            classes += f" prose-figure--{width}"
        return f'<figure class="{classes}">\n'

    def link_open(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        """A recognised video link is a button, not an anchor (F63, ADR-035).

        The `<iframe>` is built by `video.js` on the press and by nothing else:
        `iframe` is not in `ALLOWED_TAGS` and is never going in, so no path
        through the parser or the sanitiser can produce one. Until the press the
        page has asked the video host for nothing.
        """
        embed = tokens[idx].meta.get("video_embed")
        if embed is None:
            return self.renderToken(tokens, idx, options, env)

        return (
            '<button class="prose-video__play" type="button" '
            f'data-video="{escapeHtml(embed)}" '
            f'data-title="{escapeHtml(translate("prose.video_frame"))}">'
        )

    def link_close(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        if tokens[idx].meta.get("video_embed") is None:
            return self.renderToken(tokens, idx, options, env)

        # The control's own name, so it does not depend on a poster's alt text or
        # on the URL the author pasted. The triangle is text rather than a shape,
        # because a shape drawn in CSS disappears under `forced-colors`.
        label = escapeHtml(translate("prose.video_play"))
        return (
            '<span class="prose-video__glyph" aria-hidden="true">▶</span>'
            f'<span class="prose-video__label">{label}</span></button>'
        )

    def text(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        # The link text of a video paragraph: either the URL itself or the words
        # that became the caption. Neither belongs inside the button.
        if tokens[idx].meta.get("video_text"):
            return ""
        return super().text(tokens, idx, options, env)

    # A scrolling box has to be reachable without a mouse. Chrome 127+ makes
    # scroll containers focusable on its own; Firefox and Safari do not, and
    # there a wide code block or table simply cannot be read from a keyboard.
    def fence(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        return super().fence(tokens, idx, options, env).replace("<pre>", _pre_open(), 1)

    def code_block(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        return super().code_block(tokens, idx, options, env).replace("<pre>", _pre_open(), 1)

    def table_open(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        # The scroller is this wrapper, never the table: `display: block` on a
        # <table> costs it its role, its header associations and its row and
        # column counts in the accessibility tree.
        return f"{_table_scroll_open()}<table>"

    def table_close(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        return "</table></div>\n"

    def paragraph_close(self, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
        token = tokens[idx]
        image = token.meta.get("figure_image")
        if image is None and not token.meta.get("figure_video"):
            return self.renderToken(tokens, idx, options, env)

        # A video figure carries its caption already resolved — the author's link
        # text, or the poster's Markdown title. A picture's is its own title.
        caption = token.meta.get("figure_caption") or (
            image.attrGet("title") if image is not None else ""
        )
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
    # `button` is the video facade and nothing else. **`iframe` is not here and
    # is not going to be** (ADR-035): the only thing that ever builds one is
    # `video.js`, on a reader's press, so no mistake in the parser configuration
    # can turn an article into an embedding hole.
    "a", "img", "figure", "figcaption", "button",
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
    "span": {"class", "aria-hidden"},
    # The video facade. `data-video` holds a URL this module built out of an
    # anchored per-host pattern, which is the only reason it can be trusted here:
    # nh3 filters attribute names and never values (ADR-035). An author cannot
    # produce a `button` at all — raw HTML is off at the parser and
    # `attrs_plugin` reaches images only.
    "button": {"class", "type", "data-video", "data-title"},
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


_VIDEO_PLAY_BUTTON = re.compile(r'<button class="prose-video__play"[^>]*>.*?</button>', re.DOTALL)


def excerpt_from(text: str, limit: int = 220) -> str:
    """Plain-text summary for cards and meta descriptions.

    The play control's own label («Смотреть видео», ADR-038) is stripped before
    the tags are, because `nh3.clean` with an empty tag set drops the `<button>`
    but keeps the text inside it — the button and its label are removed as one
    unit, leaving any `<figcaption>` on the same figure untouched.
    """
    html = _VIDEO_PLAY_BUTTON.sub("", _md.render(text or ""))
    plain = nh3.clean(html, tags=set(), attributes={}).strip()
    plain = " ".join(plain.split())
    if len(plain) <= limit:
        return plain
    return plain[:limit].rsplit(" ", 1)[0].rstrip(",.;:—-") + "…"
