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
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from app.services.markdown import video_host

_TIMEOUT_S = 3.0

#: Each host's own public, unauthenticated oEmbed endpoint. The fetched URL is
#: always one of these two literal hosts — the submitted link reaches it only
#: as an encoded query value, never as the host being requested, so this
#: cannot be made to fetch an arbitrary address.
_OEMBED_ENDPOINTS = {
    "youtube": "https://www.youtube.com/oembed?format=json&url={url}",
    "rutube": "https://rutube.ru/api/oembed/?format=json&url={url}",
}


def video_title(href: str) -> str | None:
    """The title `href`'s own host reports for it, or None.

    None for anything that is not a recognised YouTube or RuTube link
    (`video_host` — the same anchored patterns the renderer matches against),
    and None for a network failure, a timeout, a non-200 response or a
    response with no usable title. Every failure mode answers "no title";
    nothing here raises past this function.
    """
    endpoint = _OEMBED_ENDPOINTS.get(video_host(href) or "")
    if endpoint is None:
        return None

    target = endpoint.format(url=quote(href.strip(), safe=""))
    try:
        with urlopen(target, timeout=_TIMEOUT_S) as response:
            if response.status != 200:
                return None
            body = json.loads(response.read())
    except (URLError, OSError, ValueError):
        return None

    title = body.get("title") if isinstance(body, dict) else None
    return title.strip() if isinstance(title, str) and title.strip() else None
