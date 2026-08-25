"""Server-side oEmbed title lookup for YouTube/RuTube links (F66, ADR-040).

Never a real network call: `urlopen` is monkeypatched to a fake that records
the URL it was asked to fetch and returns a canned body, so these tests prove
what gets requested and what a failure returns — not that the internet works.
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from app.services import video_title as video_title_module
from app.services.video_title import video_title

YOUTUBE_URL = "https://youtu.be/dQw4w9WgXcQ"
RUTUBE_URL = "https://rutube.ru/video/" + "a" * 32 + "/"
VK_URL = "https://vk.com/video-22822305_456241864"


class _Response:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


def _fake_urlopen(body: str, status: int = 200) -> tuple[object, list[str]]:
    """A stand-in for `urlopen` that records every URL it is asked to fetch."""
    calls: list[str] = []

    def fake(url: str, timeout: float) -> _Response:
        calls.append(url)
        return _Response(status, body.encode())

    return fake, calls


def test_a_youtube_link_is_fetched_from_youtubes_own_oembed(monkeypatch):
    fake, calls = _fake_urlopen(json.dumps({"title": "Заголовок"}))
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    assert video_title(YOUTUBE_URL) == "Заголовок"
    assert calls[0].startswith("https://www.youtube.com/oembed?")
    assert urlsplit(calls[0]).netloc == "www.youtube.com"


def test_a_rutube_link_is_fetched_from_rutubes_own_oembed(monkeypatch):
    fake, calls = _fake_urlopen(json.dumps({"title": "Название"}))
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    assert video_title(RUTUBE_URL) == "Название"
    assert urlsplit(calls[0]).netloc == "rutube.ru"


def test_a_vk_link_is_never_fetched(monkeypatch):
    """No public, unauthenticated oEmbed exists for VK (ADR-040)."""
    fake, calls = _fake_urlopen(json.dumps({"title": "x"}))
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    assert video_title(VK_URL) is None
    assert calls == []


def test_an_unrecognised_host_is_never_fetched(monkeypatch):
    fake, calls = _fake_urlopen(json.dumps({"title": "x"}))
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    assert video_title("https://vimeo.com/1234567") is None
    assert calls == []


def test_the_fetched_host_never_moves_no_matter_what_the_link_carries(monkeypatch):
    """The request target is always a `_VIDEO_SERVICES`-shaped YouTube or Rutube
    URL, never an arbitrary host taken from the input — even one that carries
    what looks like a second URL in its own query string."""
    fake, calls = _fake_urlopen(json.dumps({"title": "x"}))
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    video_title("https://youtu.be/dQw4w9WgXcQ?redirect=https://evil.example")

    assert urlsplit(calls[0]).netloc == "www.youtube.com"


def test_a_timeout_answers_no_title(monkeypatch):
    def raises(url: str, timeout: float) -> None:
        raise TimeoutError

    monkeypatch.setattr(video_title_module, "urlopen", raises)

    assert video_title(YOUTUBE_URL) is None


def test_a_non_200_response_answers_no_title(monkeypatch):
    fake, _calls = _fake_urlopen(json.dumps({"title": "x"}), status=404)
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    assert video_title(YOUTUBE_URL) is None


def test_a_blank_title_answers_none(monkeypatch):
    fake, _calls = _fake_urlopen(json.dumps({"title": "   "}))
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    assert video_title(YOUTUBE_URL) is None


def test_unparseable_json_answers_no_title(monkeypatch):
    fake, _calls = _fake_urlopen("not json")
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    assert video_title(YOUTUBE_URL) is None


def test_an_overlong_link_is_never_fetched(monkeypatch):
    """A many-kilobyte `url` field does no regex work and no round trip."""
    fake, calls = _fake_urlopen(json.dumps({"title": "x"}))
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    overlong = YOUTUBE_URL + "?" + "a" * 3000
    assert video_title(overlong) is None
    assert calls == []


def test_a_title_carrying_markdown_syntax_is_escaped(monkeypatch):
    """A third party's own text must not restructure the link it becomes."""
    fake, _calls = _fake_urlopen(json.dumps({"title": "Название] (https://evil.example) [x"}))
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    caption = video_title(YOUTUBE_URL)

    assert caption == r"Название\] \(https://evil.example\) \[x"
    assert "](" not in caption


def test_an_overlong_title_is_capped(monkeypatch):
    fake, _calls = _fake_urlopen(json.dumps({"title": "слово " * 100}))
    monkeypatch.setattr(video_title_module, "urlopen", fake)

    caption = video_title(YOUTUBE_URL)

    assert caption is not None
    assert len(caption) <= 201
    assert caption.endswith("…")
