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

Two files' worth of lifecycle lives here as well, because they are one design
(ADR-013). `media_asset` keys a stored upload by the SHA-256 of its bytes, so
the same frame used twice is written once; `release` deletes a stem only after
asking the content tables whether anything still points at it. Neither keeps a
count: a count can drift, and drifting low deletes a file that is still on a
page.
"""

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.media_asset import MediaAsset
from app.models.photo import Photo
from app.models.post import Post
from app.models.project import Project
from app.models.site_content import SiteContent
from app.templating import translate

logger = logging.getLogger("portfolio.images")

# HEIC is what an iPhone produces by default, and refusing it made the owner
# convert every file before uploading it (SPEC F51, roadmap R-10). `pillow-heif`
# ships libheif inside its wheel, so this costs a Python dependency and no apt
# package. The decode happens at intake and nothing downstream learns a new
# format: the derivatives are WebP exactly as before, and AVIF output stays
# deferred by ADR-019.
register_heif_opener()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}

#: Hard ceiling on pixel count, independent of Pillow's own bomb thresholds.
#: 120 Mp is far above anything the owner's cameras produce and far below what
#: it takes to exhaust a worker: at four bytes a pixel this is ~480 MB decoded.
MAX_PIXELS = 120_000_000

# Magic bytes, checked because a client-supplied content type proves nothing.
_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)

#: HEIF is ISO-BMFF: no leading signature, but `ftyp` at offset 4 and a brand at
#: 8 naming the flavour. Only the still-image brands are accepted; `mif1` and
#: `msf1` are the generic ones an iPhone also writes.
_HEIF_BRANDS = frozenset(
    {b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevm", b"hevs", b"mif1", b"msf1"}
)


#: At or below this width a rendition is a thumbnail: shown at a few hundred CSS
#: pixels in a grid and never opened on its own.
THUMBNAIL_WIDTH = 640

#: What a thumbnail is written at, whatever its profile asks for. Quality 92 on
#: the 640 rung measured 134 KB against this project's 120 KB budget — a 40%
#: heavier grid for a difference invisible at the size it is displayed. ADR-014
#: asks for the owner's frames to be shown at their best; that is a statement
#: about the picture you open, and `sizes` keeps the grid off it.
THUMBNAIL_QUALITY = 82


@dataclass(frozen=True, slots=True)
class Profile:
    """A rendition ladder and the quality it is written at."""

    widths: tuple[int, ...]
    quality: int
    native: bool = False

    def quality_for(self, width: int) -> int:
        """The quality one rung is written at."""
        return THUMBNAIL_QUALITY if width <= THUMBNAIL_WIDTH else self.quality

    def widths_for(self, source_width: int) -> tuple[int, ...]:
        """The renditions this profile produces for a source of the given width.

        Nothing is ever upscaled, so every rung above the source drops out.
        `native` adds the source's own width — the whole point of the
        photography profile — and a source below every rung still gets exactly
        one rendition, because something has to be servable.
        """
        widths = {width for width in self.widths if width <= source_width}
        if self.native or not widths:
            widths.add(source_width)
        return tuple(sorted(widths))


#: Album photographs. The owner prepares his own frames and asked for them to be
#: shown at their best, so the top of the ladder is the original's own width at a
#: quality where re-compression is not visible. Serving the uploaded file itself
#: is not an option: `/media` is mounted over `derived/` only, and that is what
#: keeps an original unreachable structurally rather than by rule (ADR-014).
PHOTO = Profile((640, 1600, 2560), quality=92, native=True)

#: Pictures inside an article or a project description. 1920 px is where more
#: pixels stop being visible in a column of prose.
PROSE = Profile((640, 1280, 1920), quality=85)

#: Covers. A card and an Open Graph image, never a full-bleed photograph.
COVER = Profile((640, 1600), quality=85)

# The logical parents. Plural, because each holds many albums or articles.
PHOTOS = "photos"
POSTS = "posts"
PROJECTS = "projects"

# Files whose owner is not known yet — an image dropped into an article that
# has not been saved. Rare, and it keeps such files out of everyone else's way.
UNFILED = "_unfiled"

_UNSAFE_IN_GROUP = re.compile(r"[^a-z0-9_-]+")
GROUP_MAX = 60

#: The `_<width>` a rendition's name ends with, stripped to get back to a stem.
_RENDITION_SUFFIX = re.compile(r"_\d{1,5}$")

#: A `/media/<stem>_<width>.webp` URL as it appears in stored Markdown or HTML.
#: The stem is captured; the width is not, because the point is which upload the
#: text refers to, not which rendition of it happens to be quoted.
_MEDIA_IN_TEXT = re.compile(r"/media/([^\s\"'<>()]+?)_\d{1,5}\.webp")


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
    if data[4:8] == b"ftyp" and data[8:12] in _HEIF_BRANDS:
        return "image/heic"
    return None


def validate_upload(filename: str, content_type: str | None, data: bytes) -> str:
    """Check an upload before anything touches the disk. Returns the real MIME type."""
    if not data:
        raise ImageRejected(translate("image.empty"))

    if len(data) > settings.max_upload_bytes:
        raise ImageRejected(translate("image.too_large", limit=settings.max_upload_mb))

    extension = Path(filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ImageRejected(translate("image.wrong_type"))

    if content_type and content_type.split(";")[0].strip() not in ALLOWED_CONTENT_TYPES:
        raise ImageRejected(translate("image.wrong_type"))

    sniffed = _sniff(data)
    if sniffed is None:
        raise ImageRejected(translate("image.not_an_image"))

    return sniffed


def resolve_inside(root: Path, relative: str) -> Path:
    """Resolve a media-relative path, refusing anything that escapes the root."""
    root = root.resolve()
    target = (root / relative).resolve()
    if root != target and root not in target.parents:
        raise ImageRejected(translate("image.bad_path"))
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


def stem_of(relative: str) -> str:
    """The stem shared by one upload's original and every rendition of it.

    `photos/3-elbrus/ab12.jpg` and `photos/3-elbrus/ab12_1600.webp` both give
    `photos/3-elbrus/ab12`. Stored paths always use forward slashes, because
    they are built here and never by the platform's path joiner.
    """
    without_extension = relative.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    parent = relative.rsplit("/", 1)[0] if "/" in relative else ""
    stem = _RENDITION_SUFFIX.sub("", without_extension)
    return f"{parent}/{stem}" if parent else stem


def renditions_of(stem: str) -> dict[int, str]:
    """Every `<stem>_<width>.webp` that is actually on disk, by glob.

    Never by rebuilding the ladder from a width tuple. The tuple that produced a
    file is not necessarily the tuple in force today — `blog.py` used to guess
    `_640.webp` with a regex, which worked only while one constant happened to
    hold two particular numbers — and a reconstructed list silently misses
    whatever the profiles have changed since.
    """
    try:
        directory = resolve_inside(settings.derived_dir, stem).parent
    except ImageRejected:
        return {}

    prefix = stem.rsplit("/", 1)[-1]
    found: dict[int, str] = {}
    for path in directory.glob(f"{prefix}_*.webp"):
        width = path.stem.rsplit("_", 1)[-1]
        if width.isdigit():
            found[int(width)] = f"{stem}_{width}.webp"
    return found


def stems_in_text(*texts: str | None) -> set[str]:
    """Every stem referenced by `/media/…` URLs inside stored prose.

    Read both `body_md` **and** `body_html`: a rendered article keeps its own
    copy of the URL, and a check that reads only the Markdown will happily
    delete a picture that is still on the published page.
    """
    return {match for text in texts if text for match in _MEDIA_IN_TEXT.findall(text)}


def content_digest(data: bytes) -> str:
    """The identity of an upload: the SHA-256 of the bytes we were given."""
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    """The same identity, for a file already on disk.

    Read in chunks rather than whole: the background pool renders 50 MB frames
    and there is no reason for the hash to hold one in memory as well.
    """
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def stored_from_asset(asset: MediaAsset) -> StoredImage:
    """Describe an already-stored upload as though we had just processed it."""
    return StoredImage(
        original_path=asset.original_path,
        derivatives=renditions_of(asset.stem),
        width=asset.width,
        height=asset.height,
        byte_size=asset.byte_size,
    )


def find_asset(db: Session, digest: str) -> MediaAsset | None:
    """The stored upload with exactly these bytes, if its files are still there.

    A row whose renditions have gone — deleted by hand, restored from a partial
    backup — is dropped instead of handed back. Reusing it would hand the caller
    URLs that 404, which is worse than storing the file a second time.
    """
    asset = db.get(MediaAsset, digest)
    if asset is None:
        return None
    if not renditions_of(asset.stem):
        db.delete(asset)
        db.flush()
        return None
    return asset


def missing_rungs(asset: MediaAsset, profile: Profile) -> tuple[int, ...]:
    """Widths `profile` asks for that this upload does not have on disk.

    Read by glob, never by comparing profiles: the ladder a file actually has
    is a fact about the disk, and the profile it came in under is not recorded
    anywhere — deliberately, because it would be one more thing free to drift.
    """
    if asset.width <= 0:
        return ()
    have = renditions_of(asset.stem)
    return tuple(width for width in profile.widths_for(asset.width) if width not in have)


def top_up(asset: MediaAsset, profile: Profile) -> StoredImage:
    """Render the rungs `profile` wants and this upload is missing.

    Deduplication is keyed on bytes, not on what the bytes were wanted for, so a
    hit can hand back a ladder built under a narrower profile. `COVER` stops at
    1600 px at quality 85; `PHOTO` wants the original's own width at 92. Without
    this, a frame used first as a cover and then in an album would be served in
    the lightbox at the cover's ceiling forever, and nothing would ever revisit
    it — ADR-014's one property that must not fail, lost to a cache hit.

    Storing the file a second time would also answer it, and would defeat F42.
    Rendering the missing rungs onto the one copy answers it without a second
    file: one upload, one URL, every ladder anyone has asked for.

    Idempotent, and cheap when there is nothing to do — `missing_rungs` is a
    glob.
    """
    if not missing_rungs(asset, profile):
        return stored_from_asset(asset)

    generate_derivatives(asset.original_path, profile=profile)
    # Described from the disk rather than from what was just rendered: what is
    # there now is the union of both ladders, and the caller must see all of it.
    return stored_from_asset(asset)


def record_asset(db: Session, digest: str, stored: StoredImage) -> None:
    """Remember these bytes, so the next upload of them writes nothing.

    Recorded only once the renditions exist, which is what lets `find_asset`
    treat a hit as immediately servable. `merge` rather than `add`, so two
    uploads of the same frame landing together settle on one row.
    """
    db.merge(
        MediaAsset(
            sha256=digest,
            stem=stem_of(stored.original_path),
            original_path=stored.original_path,
            width=stored.width,
            height=stored.height,
            byte_size=stored.byte_size,
        )
    )
    db.flush()


def store_original(
    data: bytes, mime: str, *, kind: str = PHOTOS, group: str = ""
) -> tuple[str, Path]:
    """Write the untouched upload under a server-generated name.

    The client's filename is never used for anything on disk. `kind` is the
    logical parent — `photos`, `posts`, `projects` — and `group` is the album,
    article or project the file belongs to, so that everything one of them owns
    sits in a directory of its own (F40).
    """
    extension = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/heic": ".heic",
    }[mime]
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
                raise ImageRejected(translate("image.too_many_pixels"))
            image.verify()
    except ImageRejected:
        raise
    except Exception as exc:
        raise ImageRejected(translate("image.unreadable")) from exc


def generate_derivatives(
    original_relative: str,
    *,
    profile: Profile = PHOTO,
) -> StoredImage:
    """Produce WebP renditions. Aspect ratio is preserved and nothing is upscaled.

    Every rendition mirrors the original's own relative path under `derived/`,
    so the grouping chosen at intake carries through without being restated.
    """
    source = resolve_inside(settings.originals_dir, original_relative)

    result = StoredImage(original_path=original_relative, byte_size=source.stat().st_size)

    with Image.open(source) as image:
        # Cameras record orientation in EXIF rather than rotating pixels.
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        result.width, result.height = image.size

        stem = stem_of(original_relative)
        for width in profile.widths_for(image.width):
            if width == image.width:
                # The native rendition: re-encoded, never resampled.
                rendition = image
            else:
                height = round(image.height * width / image.width)
                rendition = image.resize((width, height), Image.Resampling.LANCZOS)

            relative = f"{stem}_{width}.webp"
            absolute = resolve_inside(settings.derived_dir, relative)
            absolute.parent.mkdir(parents=True, exist_ok=True)
            rendition.save(absolute, "WEBP", quality=profile.quality_for(width), method=5)
            result.derivatives[width] = relative

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


def _unlink(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        logger.warning("could not delete %s", path)


def owners_of(db: Session, stem: str) -> list[str]:
    """Everything the site renders that still points at this stem, named.

    Asked of the same rows the pages are built from, rather than of a reference
    count, so the answer cannot drift out of step with what is on screen
    (ADR-013). Prose is searched in **both** its Markdown and its rendered HTML:
    `body_html` is written once, at save, and keeps its own copy of every URL.

    One predicate, used two ways — `release` only asks whether the list is empty,
    `scripts/media_orphans.py` prints it. Two implementations of "who still uses
    this file?" would be free to disagree, which is the drift this design exists
    to avoid.

    A handful of `LIKE '%stem%'` scans, which is nothing across the tens of rows
    a personal site holds. Past a few thousand articles this wants an index.
    """
    owners: list[str] = []

    photos = select(Photo).where(
        Photo.original_path.contains(stem, autoescape=True)
        | Photo.thumb_path.contains(stem, autoescape=True)
        | Photo.medium_path.contains(stem, autoescape=True)
        | Photo.large_path.contains(stem, autoescape=True)
    )
    owners += [f"photo {row.id} (album {row.album_id})" for row in db.scalars(photos)]

    posts = select(Post).where(
        Post.cover_path.contains(stem, autoescape=True)
        | Post.body_md.contains(stem, autoescape=True)
        | Post.body_html.contains(stem, autoescape=True)
    )
    owners += [f"post {row.id} «{row.title}»" for row in db.scalars(posts)]

    projects = select(Project).where(
        Project.cover_path.contains(stem, autoescape=True)
        | Project.body_md.contains(stem, autoescape=True)
        | Project.body_html.contains(stem, autoescape=True)
    )
    owners += [f"project {row.id} «{row.title}»" for row in db.scalars(projects)]

    blocks = select(SiteContent).where(
        SiteContent.value_md.contains(stem, autoescape=True)
        | SiteContent.value_html.contains(stem, autoescape=True)
    )
    owners += [f"site block {row.key}" for row in db.scalars(blocks)]

    return owners


def is_referenced(db: Session, stem: str) -> bool:
    """Does anything the site renders still point at this stem?"""
    return bool(owners_of(db, stem))


def _prune_upwards(directory: Path, kind_root: Path) -> None:
    """Remove directories the deletion emptied, stopping at the kind root.

    An empty `photos/3-elbrus/` is invisible to the site, but the media tree is
    something the owner backs up and reads by hand, and a deleted album that
    leaves its directory behind does not look deleted.
    """
    current = directory
    while current != kind_root and kind_root in current.parents:
        try:
            current.rmdir()
        except OSError:
            # Not empty, or not ours to remove. Either way, stop climbing.
            return
        current = current.parent


def _delete_stem(stem: str) -> None:
    """Remove one upload's original and every rendition of it."""
    kind = stem.split("/", 1)[0]
    for root in (settings.originals_dir, settings.derived_dir):
        try:
            target = resolve_inside(root, stem)
        except ImageRejected:
            continue
        directory = target.parent
        if not directory.is_dir():
            continue
        # Two globs, no width arithmetic: `<stem>.<ext>` is the original and
        # `<stem>_<width>.webp` is whatever ladder was in force when it was
        # stored, which is not necessarily the ladder in force now.
        for path in (*directory.glob(f"{target.name}.*"), *directory.glob(f"{target.name}_*.webp")):
            _unlink(path)
        _prune_upwards(directory, (root / kind).resolve())


def release(db: Session, *paths: str | None) -> None:
    """Give up a claim on stored uploads, deleting the ones nobody else uses.

    Accepts stems or any path belonging to one — a cover's rendition, an
    original — and normalises them, so a caller cannot pick the wrong end of the
    pair. Call it *after* the rows that referenced the files are committed:
    `is_referenced` reads the database, so a row still in flight reads as a live
    reference and the file is kept.
    """
    doomed = {stem_of(path) for path in paths if path}
    removed = [stem for stem in sorted(doomed) if not is_referenced(db, stem)]
    for stem in removed:
        _delete_stem(stem)
    if removed:
        # The row only ever described files; it goes when they do.
        db.query(MediaAsset).filter(MediaAsset.stem.in_(removed)).delete(synchronize_session=False)
        db.commit()


def media_url(relative: str | None) -> str | None:
    """Public URL for a stored derivative or original."""
    if not relative:
        return None
    return f"/media/{relative.lstrip('/')}"


def cover_sources(cover_path: str | None) -> dict[str, str] | None:
    """`src` plus a `srcset` over whatever renditions of a cover exist on disk.

    Found by glob, never named: a cover may be a frame already stored under a
    different profile, so the ladder behind it is not something a caller can
    state. One rendition is not a choice, and an empty `srcset` is what the
    templates expect in that case.

    Shared by the blog and by `/dev` because their cards have the same problem —
    a picture displayed at ~300 px whose widest rendition is 1600.
    """
    if not cover_path:
        return None
    url = media_url(cover_path) or ""
    found = sorted(renditions_of(stem_of(cover_path)).items())
    if len(found) < 2:
        return {"src": url, "srcset": ""}
    return {
        "src": url,
        "srcset": ", ".join(f"{media_url(relative)} {width}w" for width, relative in found),
    }


def store_and_process(
    db: Session,
    data: bytes,
    filename: str,
    content_type: str | None,
    *,
    kind: str = PHOTOS,
    group: str = "",
    profile: Profile = COVER,
) -> StoredImage:
    """Validate, store and render one image synchronously.

    Used for single images (covers, in-article pictures). Album batches go
    through the background pool instead.

    Bytes we already hold are not stored twice (F42). A hit skips storage, and
    skips rendering too whenever the ladder on disk already covers `profile` —
    but it does not hand back a shorter ladder than the caller asked for.
    `COVER` (640, 1600) and `PROSE` (640, 1280, 1920) are subsets of neither, so
    the same frame used as a cover and then in an article genuinely needs both;
    `top_up` renders the difference onto the one stored copy. One file, one URL,
    every rung anyone has asked for.
    """
    mime = validate_upload(filename, content_type, data)

    digest = content_digest(data)
    existing = find_asset(db, digest)
    if existing is not None:
        # No second copy of the file — but the ladder behind it is topped up if
        # this profile asks for a rung the first upload did not need. `COVER`
        # and `PROSE` are not subsets of one another, so the same frame used as
        # a cover and then in the text needs both.
        return top_up(existing, profile)

    relative, absolute = store_original(data, mime, kind=kind, group=group)
    try:
        verify_decodable(absolute)
        stored = generate_derivatives(relative, profile=profile)
    except Exception:
        delete_files(relative)
        raise

    record_asset(db, digest, stored)
    return stored
