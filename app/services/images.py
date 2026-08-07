"""Image intake and derivative generation.

Shared infrastructure: album photos, article covers, in-article images and
project covers all go through here, so validation and storage rules exist in
exactly one place.

Storage layout, all relative to MEDIA_ROOT:
    originals/<kind>/<group>/<uuid>.<ext>
    derived/<kind>/<group>/<uuid>_<width>.webp

`kind` is the logical parent — `photos`, `posts`, `projects` — and `group` is
the album, article or project the file belongs to, so everything one of them
owns can be found, copied or restored on its own (F40). Files used to be filed
by year, which put one album's photographs among every other album's.

The split between `originals/` and `derived/` stays above the grouping on
purpose: only `derived/` is mounted over HTTP, so an original cannot be
reached by a URL as a matter of structure rather than of vigilance.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

from app.config import settings

logger = logging.getLogger("portfolio.images")

# Accepted input formats. HEIC is deliberately absent: it would pull in an extra
# native dependency and the owner shoots camera JPEG.
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

#: Hard ceiling on pixel count, independent of Pillow's own bomb thresholds.
#: 120 Mp is far above anything the owner's cameras produce and far below what
#: it takes to exhaust a worker: at four bytes a pixel this is ~480 MB decoded.
MAX_PIXELS = 120_000_000

# Magic bytes, checked because a client-supplied content type proves nothing.
_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)

WEBP_QUALITY = 82

# The logical parents. Plural, because each holds many albums or articles.
PHOTOS = "photos"
POSTS = "posts"
PROJECTS = "projects"

# Files whose owner is not known yet — an image dropped into an article that
# has not been saved. Rare, and it keeps such files out of everyone else's way.
UNFILED = "_unfiled"

_UNSAFE_IN_GROUP = re.compile(r"[^a-z0-9_-]+")
GROUP_MAX = 60


def group_name(identifier: int | None, slug: str) -> str:
    """A directory name for one album, article or project.

    The id comes first because it is stable and unique for the life of the row;
    the slug follows because the point of grouping is that a human can find the
    right directory without consulting the database. A later rename leaves the
    directory name stale but never ambiguous — the id still identifies it.
    """
    trimmed = _UNSAFE_IN_GROUP.sub("-", slug.lower()).strip("-")[:GROUP_MAX]
    if identifier is None:
        return trimmed or UNFILED
    return f"{identifier}-{trimmed}" if trimmed else str(identifier)


def safe_group(group: str) -> str:
    """Never let a caller's group escape its parent directory."""
    cleaned = _UNSAFE_IN_GROUP.sub("-", group.lower()).strip("-")[:GROUP_MAX]
    return cleaned or UNFILED


class ImageRejected(Exception):
    """The upload is not something we are willing to store."""


@dataclass(slots=True)
class StoredImage:
    original_path: str
    derivatives: dict[int, str] = field(default_factory=dict)
    width: int = 0
    height: int = 0
    byte_size: int = 0


def _sniff(data: bytes) -> str | None:
    for prefix, content_type in _MAGIC:
        if data.startswith(prefix):
            return content_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_upload(filename: str, content_type: str | None, data: bytes) -> str:
    """Check an upload before anything touches the disk. Returns the real MIME type."""
    if not data:
        raise ImageRejected("Файл пустой.")

    if len(data) > settings.max_upload_bytes:
        raise ImageRejected(
            f"Файл больше {settings.max_upload_mb} МБ — уменьшите размер и попробуйте снова."
        )

    extension = Path(filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ImageRejected("Поддерживаются только JPEG, PNG и WebP.")

    if content_type and content_type.split(";")[0].strip() not in ALLOWED_CONTENT_TYPES:
        raise ImageRejected("Поддерживаются только JPEG, PNG и WebP.")

    sniffed = _sniff(data)
    if sniffed is None:
        raise ImageRejected("Это не похоже на изображение.")

    return sniffed


def resolve_inside(root: Path, relative: str) -> Path:
    """Resolve a media-relative path, refusing anything that escapes the root."""
    root = root.resolve()
    target = (root / relative).resolve()
    if root != target and root not in target.parents:
        raise ImageRejected("Недопустимый путь к файлу.")
    return target


def intrinsic_size(derived_relative: str) -> tuple[int, int] | None:
    """The pixel size of a rendition under `derived/`, or None if unreadable.

    Pillow reads the header, not the pixels, so this is a seek rather than a
    decode. It exists so markup can carry `width`/`height`: a lazy picture with
    no reserved height lets the text below it jump when the bytes arrive.
    """
    try:
        with Image.open(resolve_inside(settings.derived_dir, derived_relative)) as image:
            return image.size
    except (ImageRejected, OSError, ValueError):
        # Missing, outside the media root, or not an image we can read. The
        # caller falls back to markup without dimensions rather than failing.
        return None


def store_original(
    data: bytes, mime: str, *, kind: str = PHOTOS, group: str = ""
) -> tuple[str, Path]:
    """Write the untouched upload under a server-generated name.

    The client's filename is never used for anything on disk. `kind` is the
    logical parent — `photos`, `posts`, `projects` — and `group` is the album,
    article or project the file belongs to, so that everything one of them owns
    sits in a directory of its own (F40).
    """
    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime]
    relative = f"{kind}/{safe_group(group)}/{uuid.uuid4().hex}{extension}"

    absolute = resolve_inside(settings.originals_dir, relative)
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(data)
    return relative, absolute


def verify_decodable(path: Path) -> None:
    """Confirm Pillow can actually read the file. Cheap guard against fuzzed input.

    Catches broadly on purpose. The narrow tuple this used to carry —
    `UnidentifiedImageError, OSError, ValueError` — let `DecompressionBombError`
    straight through, which is not a subclass of any of them: the caller's
    `except ImageRejected` never ran, so the request became a 500 carrying an
    HTML page to a client parsing JSON, and the stored original stayed on disk.
    Everything reaching this function is untrusted input, and every way it can
    fail means the same thing to the person uploading it.
    """
    try:
        with Image.open(path) as image:
            if image.width * image.height > MAX_PIXELS:
                # Pillow only *warns* between its own limit and twice it, and a
                # warned-about image is still decoded — several bytes a pixel,
                # in a background worker where nobody is waiting to be told.
                raise ImageRejected("Слишком большое изображение — уменьшите разрешение.")
            image.verify()
    except ImageRejected:
        raise
    except Exception as exc:
        raise ImageRejected("Файл повреждён или не читается как изображение.") from exc


def generate_derivatives(
    original_relative: str,
    *,
    widths: tuple[int, ...] | None = None,
) -> StoredImage:
    """Produce WebP renditions. Aspect ratio is preserved and nothing is upscaled.

    Every rendition mirrors the original's own relative path under `derived/`,
    so the grouping chosen at intake carries through without being restated.
    """
    widths = widths or settings.derivative_widths
    source = resolve_inside(settings.originals_dir, original_relative)

    result = StoredImage(original_path=original_relative, byte_size=source.stat().st_size)

    with Image.open(source) as image:
        # Cameras record orientation in EXIF rather than rotating pixels.
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        result.width, result.height = image.size

        stem = Path(original_relative).with_suffix("")
        for width in widths:
            if width > image.width:
                # Never upscale: a 900px original gets no 1600px rendition.
                continue

            height = round(image.height * width / image.width)
            rendition = image.resize((width, height), Image.Resampling.LANCZOS)

            relative = f"{stem}_{width}.webp"
            absolute = resolve_inside(settings.derived_dir, relative)
            absolute.parent.mkdir(parents=True, exist_ok=True)
            rendition.save(absolute, "WEBP", quality=WEBP_QUALITY, method=5)
            result.derivatives[width] = relative

        # A small original still needs something to serve.
        if not result.derivatives:
            relative = f"{stem}_{image.width}.webp"
            absolute = resolve_inside(settings.derived_dir, relative)
            absolute.parent.mkdir(parents=True, exist_ok=True)
            image.save(absolute, "WEBP", quality=WEBP_QUALITY, method=5)
            result.derivatives[image.width] = relative

    return result


def delete_files(*relative_paths: str | None) -> None:
    """Remove media files, tolerating ones that are already gone."""
    for relative in relative_paths:
        if not relative:
            continue
        for root in (settings.originals_dir, settings.derived_dir):
            try:
                candidate = resolve_inside(root, relative)
            except ImageRejected:
                continue
            if candidate.is_file():
                try:
                    candidate.unlink()
                except OSError:
                    logger.warning("could not delete %s", candidate)


def media_url(relative: str | None) -> str | None:
    """Public URL for a stored derivative or original."""
    if not relative:
        return None
    return f"/media/{relative.lstrip('/')}"


def store_and_process(
    data: bytes,
    filename: str,
    content_type: str | None,
    *,
    kind: str = PHOTOS,
    group: str = "",
    widths: tuple[int, ...] | None = None,
) -> StoredImage:
    """Validate, store and render one image synchronously.

    Used for single images (covers, in-article pictures). Album batches go
    through the background pool instead.
    """
    mime = validate_upload(filename, content_type, data)
    relative, absolute = store_original(data, mime, kind=kind, group=group)
    try:
        verify_decodable(absolute)
        return generate_derivatives(relative, widths=widths)
    except Exception:
        delete_files(relative)
        raise
