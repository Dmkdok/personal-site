"""Markdown → sanitised HTML.

Shared by the blog, project descriptions and editable site copy, so the preview
in the editor and the published page can never diverge: they call this.

Raw HTML is disabled at the parser level *and* the output is passed through an
allow-list sanitiser. Either alone would probably do; both is cheap.
"""

import nh3
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True}).enable(
    ["table", "strikethrough", "linkify", "replacements", "smartquotes"]
)

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
    "span",
}
# fmt: on

ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    # No "rel" here: nh3 rejects it in the allow-list when link_rel is set, and
    # sets rel="noopener noreferrer" on every link itself.
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height", "loading", "decoding"},
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
