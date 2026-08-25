"""One-time oEmbed title lookup for YouTube and RuTube links (F66, ADR-040).

Fetched once, server-side, at edit time, when the owner pastes a video link
into the caption snippet T142 inserts — never while a page is being served to
a reader, and never on every keystroke of the preview (that is exactly the
reader-facing request F63 was written to rule out). VK has no public,
unauthenticated oEmbed endpoint to ask, so a VK link is not attempted here;
the manual caption T142 already offers is what it gets.
"""

from __future__ import annotations

import json
import re
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from app.services.markdown import video_host

_TIMEOUT_S = 3.0

#: A pasted link is never this long; refusing early keeps a many-kilobyte
#: `url` field from doing regex work and a percent-encoded round trip for
#: nothing (a POST body this route reads has no other size limit).
_MAX_HREF = 2048

#: Read cap on the oEmbed response body. The timeout bounds how long a single
#: socket operation may take, not the whole transfer — a host trickling bytes
#: forever would otherwise hold a thread-pool worker past it.
_MAX_RESPONSE_BYTES = 64 * 1024

#: The caption is Markdown source the owner can still edit, but it starts
#: life as a third party's own text — closed the same way `WIDTH_WORDS` closes
#: the class attribute: syntax characters escaped, not trusted to be absent.
_MARKDOWN_SYNTAX = re.compile(r"[\[\]()]")
_MAX_TITLE = 200

#: Each host's own public, unauthenticated oEmbed endpoint. The fetched URL is
#: always one of these two literal hosts — the submitted link reaches it only
#: as an encoded query value, never as the host being requested, so this
#: cannot be made to fetch an arbitrary address.
_OEMBED_ENDPOINTS = {
    "youtube": "https://www.youtube.com/oembed?format=json&url={url}",
    "rutube": "https://rutube.ru/api/oembed/?format=json&url={url}",
}


def _as_caption(title: str) -> str | None:
    """`title`, made safe as a Markdown link's caption text, or None."""
    plain = " ".join(title.split())
    if not plain:
        return None
    plain = _MARKDOWN_SYNTAX.sub(lambda m: "\\" + m.group(), plain)
    if len(plain) > _MAX_TITLE:
        plain = plain[:_MAX_TITLE].rstrip() + "…"
    return plain


def video_title(href: str) -> str | None:
    """The title `href`'s own host reports for it, or None.

    None for anything that is not a recognised YouTube or RuTube link
    (`video_host` — the same anchored patterns the renderer matches against),
    and None for a network failure, a timeout, a non-200 response or a
    response with no usable title. Every failure mode answers "no title";
    nothing here raises past this function.
    """
    href = href.strip()
    if not href or len(href) > _MAX_HREF:
        return None

    endpoint = _OEMBED_ENDPOINTS.get(video_host(href) or "")
    if endpoint is None:
        return None

    target = endpoint.format(url=quote(href, safe=""))
    try:
        with urlopen(target, timeout=_TIMEOUT_S) as response:
            if response.status != 200:
                return None
            body = json.loads(response.read(_MAX_RESPONSE_BYTES))
    except (URLError, OSError, ValueError):
        return None

    title = body.get("title") if isinstance(body, dict) else None
    return _as_caption(title) if isinstance(title, str) else None
