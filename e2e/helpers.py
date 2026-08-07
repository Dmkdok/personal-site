"""Shared helpers for the Playwright suite.

Nothing user-visible is written here in Russian by accident: the few Russian
strings the tests need are accessible names, and they are read from
`app/i18n/ru/*.json` through `ru()` rather than typed twice.
"""

from __future__ import annotations

import io
import json
import random
import re
import string
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image
from playwright.sync_api import APIRequestContext, Page

ROOT = Path(__file__).resolve().parent.parent
I18N = ROOT / "app" / "i18n" / "ru"


# --------------------------------------------------------------------- strings
@lru_cache(maxsize=1)
def _catalog() -> dict:
    """The merged Russian catalogue — one file per feature area, as the app loads it."""
    merged: dict = {}
    for path in sorted(I18N.glob("*.json")):
        for key, value in json.loads(path.read_text(encoding="utf-8")).items():
            # One level deep, exactly like app.templating: `common.json` and
            # `blog.json` both own a top-level "blog" object, and a shallow
            # update would throw one of them away.
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = value
    return merged


def ru(key: str, **params: object) -> str:
    """Read a UI string the way the app does: `ru("photo.publish")`.

    Guessing the Russian wording in a selector is how an e2e suite ends up
    testing its own copy of the product.
    """
    node: object = _catalog()
    for part in key.split("."):
        assert isinstance(node, dict), f"i18n key {key!r} is not a leaf"
        node = node[part]
    assert isinstance(node, str), f"i18n key {key!r} is not a string"
    text = node
    for name, value in params.items():
        text = text.replace("{" + name + "}", str(value))
    return text


def token(length: int = 9) -> str:
    """A run-unique word that survives PostgreSQL's Russian text search.

    Latin letters only: the document and the query go through the same
    `russian` configuration, so an unknown all-letter word stems to itself on
    both sides and cannot be swallowed as a stopword.
    """
    rng = random.SystemRandom()
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(length))


# ---------------------------------------------------------------------- images
#: Finest octave, in samples across the frame. Calibrated so the pipeline's
#: 640px WebP lands at ~95 KB — the heavy end of what a detailed landscape
#: photograph weighs, and therefore a real test of the ≤120 KB budget rather
#: than a rubber stamp. Pixel-level noise is the wrong shape: it averages away
#: in the downscale and produced a 15 KB thumbnail that proved nothing.
_FINEST_OCTAVE = 256


def _octaves(width: int, height: int, seed: int) -> Image.Image:
    """Fractal noise — structure at every scale, so detail survives a resize."""
    rng = random.Random(seed)
    layer = Image.new("L", (width, height), 128)
    size = 4
    while size <= _FINEST_OCTAVE:
        noise = Image.effect_noise(
            (size, max(2, size * height // width)), rng.uniform(70, 95)
        ).resize((width, height), Image.BICUBIC)
        layer = Image.blend(layer, noise, 0.5)
        size *= 2
    return layer


@lru_cache(maxsize=64)
def photo_bytes(width: int = 2400, height: int = 1600, seed: int = 0) -> bytes:
    """A JPEG with photograph-like entropy at every scale."""
    frame = Image.merge("RGB", [_octaves(width, height, seed * 7 + band) for band in range(3)])
    buffer = io.BytesIO()
    frame.save(buffer, "JPEG", quality=90)
    return buffer.getvalue()


# ------------------------------------------------------------------- admin API
@dataclass
class Album:
    id: int
    slug: str
    title: str


@dataclass
class Post:
    id: int
    slug: str
    title: str


class AdminApi:
    """Direct HTTP against the admin endpoints, sharing the browser session.

    Used to *arrange* fixtures and to clean up afterwards. The flows under test
    are always driven through the UI — arranging them by clicking would make a
    lightbox failure look like an upload failure.
    """

    def __init__(self, request: APIRequestContext) -> None:
        self._request = request
        self._token: str | None = None

    # -- plumbing ---------------------------------------------------------
    @property
    def csrf(self) -> str:
        if self._token is None:
            html = self._request.get("/").text()
            match = re.search(r'X-CSRF-Token":\s*"([^"]+)"', html)
            assert match, "no CSRF token on the home page — is the session still valid?"
            self._token = match.group(1)
        return self._token

    def _headers(self) -> dict[str, str]:
        return {"X-CSRF-Token": self.csrf}

    def get(self, path: str):
        return self._request.get(path)

    # -- albums -----------------------------------------------------------
    def create_album(self, title: str, caption: str = "") -> Album:
        response = self._request.post(
            "/photo/admin/albums",
            form={"title": title, "caption": caption},
            headers=self._headers(),
        )
        assert response.status == 200, f"create_album → {response.status}: {response.text()[:300]}"
        slug = response.headers["hx-redirect"].rsplit("/", 1)[-1]
        page = self._request.get(f"/photo/{slug}").text()
        match = re.search(r'data-upload-url="/photo/admin/albums/(\d+)/photos"', page)
        assert match, "album page carries no upload zone — not signed in?"
        return Album(id=int(match.group(1)), slug=slug, title=title)

    def upload_photo(self, album: Album, data: bytes, name: str) -> int:
        response = self._request.post(
            f"/photo/admin/albums/{album.id}/photos",
            multipart={"file": {"name": name, "mimeType": "image/jpeg", "buffer": data}},
            headers=self._headers(),
        )
        assert response.status == 201, f"upload → {response.status}: {response.text()[:300]}"
        return response.json()["id"]

    def grid_html(self, album: Album) -> str:
        return self._request.get(f"/photo/admin/albums/{album.id}/grid").text()

    def ready_count(self, album: Album) -> tuple[int, int]:
        """(ready, still in flight) as the owner's grid reports them."""
        html = self.grid_html(album)
        statuses = re.findall(r'data-status="(\w+)"', html)
        ready = sum(1 for s in statuses if s == "ready")
        waiting = sum(1 for s in statuses if s in {"pending", "processing"})
        return ready, waiting

    def publish_album(self, album: Album) -> None:
        response = self._request.post(
            f"/photo/admin/albums/{album.id}/publish", headers=self._headers()
        )
        assert response.status == 200, f"publish album → {response.status}"

    def delete_album(self, album_id: int) -> None:
        self._request.delete(f"/photo/admin/albums/{album_id}", headers=self._headers())

    # -- posts ------------------------------------------------------------
    def create_post(self, title: str) -> Post:
        response = self._request.post(
            "/blog/admin/posts", form={"title": title}, headers=self._headers()
        )
        assert response.status == 204, f"create_post → {response.status}"
        slug = response.headers["hx-redirect"].split("/")[2]
        editor = self._request.get(f"/blog/{slug}/edit").text()
        match = re.search(r'hx-post="/blog/admin/posts/(\d+)"', editor)
        assert match, "editor page carries no post id"
        return Post(id=int(match.group(1)), slug=slug, title=title)

    def upload_inline_image(self, post: Post, data: bytes, name: str) -> str:
        """Store a picture for the body of `post` and return its `/media/…` URL."""
        response = self._request.post(
            "/blog/admin/images",
            multipart={
                "file": {"name": name, "mimeType": "image/jpeg", "buffer": data},
                "post_id": str(post.id),
            },
            headers=self._headers(),
        )
        assert response.status == 200, f"inline image → {response.status}: {response.text()[:300]}"
        return response.json()["url"]

    def publish_post(self, post: Post, body_md: str = "") -> None:
        response = self._request.post(
            f"/blog/admin/posts/{post.id}/publish",
            form={"title": post.title, "slug": post.slug, "excerpt": "", "body_md": body_md},
            headers=self._headers(),
        )
        assert response.status == 200, f"publish post → {response.status}"

    def delete_post(self, post_id: int) -> None:
        self._request.post(f"/blog/admin/posts/{post_id}/delete", headers=self._headers())


# ------------------------------------------------------------------ page utils
def csrf_of(page: Page) -> str:
    return page.evaluate(
        "() => JSON.parse(document.body.getAttribute('hx-headers') || '{}')['X-CSRF-Token'] || ''"
    )


def theme_of(page: Page) -> str | None:
    return page.evaluate("() => document.documentElement.dataset.theme || null")


# --------------------------------------------------------------------- colours
def srgb_to_linear(channel: float) -> float:
    channel /= 255.0
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[float, float, float], bg: tuple[float, float, float]) -> float:
    a, b = relative_luminance(fg), relative_luminance(bg)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


_RGB = re.compile(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,/\s]+([\d.]+))?")
# `light-dark()` resolves to the modern syntax in Chromium, with 0–1 channels.
_SRGB = re.compile(r"color\(\s*srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*/\s*([\d.]+))?")

RGBA = tuple[float, float, float, float]


def parse_rgb(value: str) -> RGBA:
    text = value.strip()
    if text in {"transparent", "rgba(0, 0, 0, 0)"}:
        return (0.0, 0.0, 0.0, 0.0)

    match = _RGB.match(text)
    if match:
        r, g, b, a = match.groups()
        return float(r), float(g), float(b), float(a) if a is not None else 1.0

    match = _SRGB.match(text)
    if match:
        r, g, b, a = match.groups()
        return (
            float(r) * 255,
            float(g) * 255,
            float(b) * 255,
            float(a) if a is not None else 1.0,
        )

    raise AssertionError(f"unparsable colour {value!r}")


def over(top: RGBA, bottom: RGBA) -> RGBA:
    """Source-over compositing of two straight-alpha colours."""
    alpha = top[3] + bottom[3] * (1 - top[3])
    if alpha == 0:
        return (0.0, 0.0, 0.0, 0.0)
    channels = tuple(
        (top[i] * top[3] + bottom[i] * bottom[3] * (1 - top[3])) / alpha for i in range(3)
    )
    return (*channels, alpha)


def composite(layers: list[str]) -> tuple[float, float, float]:
    """Flatten a stack of CSS colours, topmost first, onto white."""
    result: RGBA = (255.0, 255.0, 255.0, 1.0)
    for value in reversed(layers):
        result = over(parse_rgb(value), result)
    return result[:3]


def flatten(fg: str, backdrop: list[str]) -> tuple[float, float, float]:
    """The colour a translucent foreground actually paints on this backdrop."""
    return composite([fg, *backdrop])
