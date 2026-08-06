"""Image intake and derivative generation.

Shared infrastructure: album photos, article covers, in-article images and
project covers all go through here, so validation and storage rules exist in
exactly one place.

Storage layout, all relative to MEDIA_ROOT:
    originals/<kind>/<yyyy>/<uuid>.<ext>
    derived/<kind>/<yyyy>/<uuid>_<width>.webp
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

logger = logging.getLogger("portfolio.images")

# Accepted input formats. HEIC is deliberately absent: it would pull in an extra
# native dependency and the owner shoots camera JPEG.
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Magic bytes, checked because a client-supplied content type proves nothing.
_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)

WEBP_QUALITY = 82


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


def _resolve_inside(root: Path, relative: str) -> Path:
    """Resolve a media-relative path, refusing anything that escapes the root."""
    root = root.resolve()
    target = (root / relative).resolve()
    if root != target and root not in target.parents:
        raise ImageRejected("Недопустимый путь к файлу.")
    return target


def store_original(data: bytes, mime: str, *, kind: str = "album") -> tuple[str, Path]:
    """Write the untouched upload under a server-generated name.

    The client's filename is never used for anything on disk.
    """
    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime]
    year = datetime.now(UTC).strftime("%Y")
    relative = f"{kind}/{year}/{uuid.uuid4().hex}{extension}"

    absolute = _resolve_inside(settings.originals_dir, relative)
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(data)
    return relative, absolute


def verify_decodable(path: Path) -> None:
    """Confirm Pillow can actually read the file. Cheap guard against fuzzed input."""
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageRejected("Файл повреждён или не читается как изображение.") from exc


def generate_derivatives(
    original_relative: str,
    *,
    kind: str = "album",
    widths: tuple[int, ...] | None = None,
) -> StoredImage:
    """Produce WebP renditions. Aspect ratio is preserved and nothing is upscaled."""
    widths = widths or settings.derivative_widths
    source = _resolve_inside(settings.originals_dir, original_relative)

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
            absolute = _resolve_inside(settings.derived_dir, relative)
            absolute.parent.mkdir(parents=True, exist_ok=True)
            rendition.save(absolute, "WEBP", quality=WEBP_QUALITY, method=5)
            result.derivatives[width] = relative

        # A small original still needs something to serve.
        if not result.derivatives:
            relative = f"{stem}_{image.width}.webp"
            absolute = _resolve_inside(settings.derived_dir, relative)
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
                candidate = _resolve_inside(root, relative)
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
    kind: str = "album",
    widths: tuple[int, ...] | None = None,
) -> StoredImage:
    """Validate, store and render one image synchronously.

    Used for single images (covers, in-article pictures). Album batches go
    through the background pool instead.
    """
    mime = validate_upload(filename, content_type, data)
    relative, absolute = store_original(data, mime, kind=kind)
    try:
        verify_decodable(absolute)
        return generate_derivatives(relative, kind=kind, widths=widths)
    except Exception:
        delete_files(relative)
        raise
