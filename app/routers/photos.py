"""Photography: albums, photos, uploads. Public pages plus in-place admin.

Everything the owner does — create an album, drop a batch of files, reorder,
set a cover, publish — happens on the public page through htmx swaps of the
partials in `templates/photo/`. Uploads are the exception: each file rides its
own XMLHttpRequest so `uploader.js` can show real per-file progress, and the
answer is JSON rather than a fragment.

Derivative generation runs off the request path (`background.submit_with_session`)
and the grid polls until nothing is pending. A restart that interrupts the batch
is repaired by `recover_stuck_photos`, registered as a startup recovery hook.
"""

import logging
import re
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import background
from app.config import settings
from app.db import SessionLocal
from app.deps import CurrentAdmin, DbSession, OptionalAdmin
from app.models.album import Album
from app.models.photo import Photo, PhotoStatus
from app.services import images
from app.services.slugs import unique_slug
from app.templating import render, toast_headers, translate

logger = logging.getLogger("portfolio.photo")

router = APIRouter(prefix="/photo", tags=["photo"])

# Storage bucket under MEDIA_ROOT. Album photos are the only batch uploads.
PHOTO_KIND = images.PHOTOS

MAX_TITLE = 200
MAX_CAPTION = 600
MAX_ALT = 300

# Statuses that mean "the pipeline still owes this photo an answer".
IN_FLIGHT = (PhotoStatus.PENDING, PhotoStatus.PROCESSING)

# `images` names every rendition `<stem>_<width>.webp`, so the width a file was
# rendered at is recoverable from its name — no extra columns needed for srcset.
_WIDTH_IN_NAME = re.compile(r"_(\d+)\.webp$")

# The grid lays photos out at their own aspect ratio. Snapping to the standard
# photographic ratios keeps that in a stylesheet class instead of an inline
# style, which the Content-Security-Policy forbids. Cameras shoot 3:2 or 4:3,
# so for real photographs the snap is usually exact.
_RATIO_BUCKETS = (
    (0.5625, "9x16"),
    (0.6667, "2x3"),
    (0.75, "3x4"),
    (1.0, "1x1"),
    (1.3333, "4x3"),
    (1.5, "3x2"),
    (1.7778, "16x9"),
    (2.3333, "21x9"),
)
DEFAULT_RATIO_CLASS = "3x2"

_STATE_KEYS = {
    # PENDING means "uploaded, waiting for the pool" — from the owner's side
    # that is indistinguishable from processing, so it reads the same.
    PhotoStatus.PENDING: "photo.state_processing",
    PhotoStatus.PROCESSING: "photo.state_processing",
    PhotoStatus.READY: "photo.state_ready",
    PhotoStatus.FAILED: "photo.state_failed",
}


class AlbumInvalid(Exception):
    """Input the owner can fix. Reported inline, never as a traceback."""


# --------------------------------------------------------------------------
# Template helpers
# --------------------------------------------------------------------------
def ratio_class(photo: Photo) -> str:
    """The nearest standard aspect ratio, as a CSS modifier suffix."""
    if not photo.width or not photo.height:
        return DEFAULT_RATIO_CLASS
    ratio = photo.width / photo.height
    return min(_RATIO_BUCKETS, key=lambda bucket: abs(bucket[0] - ratio))[1]


def srcset(photo: Photo) -> str:
    """A `srcset` over whatever renditions this photo actually has.

    A small original yields one rendition, a large one yields three; the width
    descriptors come from the filenames so the browser can pick honestly.
    """
    parts: list[str] = []
    seen: set[str] = set()
    for path in (photo.thumb_path, photo.medium_path, photo.large_path):
        if not path or path in seen:
            continue
        seen.add(path)
        match = _WIDTH_IN_NAME.search(path)
        if match:
            parts.append(f"{images.media_url(path)} {match.group(1)}w")
    return ", ".join(parts)


def display_src(photo: Photo) -> str | None:
    """The largest rendition available — what the lightbox opens."""
    return images.media_url(photo.large_path or photo.medium_path or photo.thumb_path)


def state_label(photo: Photo) -> str:
    return translate(_STATE_KEYS[photo.status])


def photo_alt(photo: Photo, album: Album) -> str:
    """Never ship an empty alt on content imagery: fall back to the album."""
    return photo.alt or translate("photo.photo_alt_fallback", title=album.title)


def _helpers() -> dict[str, Any]:
    return {
        "media_url": images.media_url,
        "ratio_class": ratio_class,
        "srcset": srcset,
        "display_src": display_src,
        "state_label": state_label,
        "photo_alt": photo_alt,
    }


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
def _visible_albums(db: Session, admin: Any) -> list[Album]:
    """Albums in the owner's order. Visitors never see unpublished ones."""
    query = (
        select(Album).options(selectinload(Album.cover_photo)).order_by(Album.sort_order, Album.id)
    )
    if admin is None:
        query = query.where(Album.is_published.is_(True))
    return list(db.scalars(query))


def _get_album(db: Session, album_id: int) -> Album:
    album = db.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail=translate("photo.not_found"))
    return album


def _get_photo(db: Session, photo_id: int) -> Photo:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail=translate("photo.photo_not_found"))
    return photo


def _album_photos(db: Session, album: Album, admin: Any) -> list[Photo]:
    """Photos in the owner's order.

    A visitor only ever sees finished work; the owner also sees what is still
    processing or has failed, because that is what the retry action hangs off.
    """
    query = select(Photo).where(Photo.album_id == album.id).order_by(Photo.sort_order, Photo.id)
    if admin is None:
        query = query.where(Photo.status == PhotoStatus.READY)
    return list(db.scalars(query))


# --------------------------------------------------------------------------
# Response shapes
# --------------------------------------------------------------------------
def _index_context(db: Session, admin: Any, form: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "active_section": "photo",
        "albums": _visible_albums(db, admin),
        "form": form,
        **_helpers(),
    }


def _album_context(
    db: Session, album: Album, admin: Any, form: dict[str, Any] | None = None
) -> dict[str, Any]:
    photos = _album_photos(db, album, admin)
    return {
        "active_section": "photo",
        "album": album,
        "photos": photos,
        # Drives the grid's polling: the wrapper stops emitting `every 2s` the
        # moment nothing is left for the pipeline to answer for.
        "pending": any(photo.status in IN_FLIGHT for photo in photos),
        "form": form,
        **_helpers(),
    }


def _board(
    request: Request,
    db: Session,
    admin: Any,
    *,
    form: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> HTMLResponse:
    """The whole album index surface: the open form, if any, plus the cards."""
    return render(
        request, "photo/_board.html", _index_context(db, admin, form), admin=admin, headers=headers
    )


def _head(
    request: Request,
    db: Session,
    album: Album,
    admin: Any,
    *,
    form: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> HTMLResponse:
    """The album's title block plus its admin actions."""
    return render(
        request,
        "photo/_album_head.html",
        _album_context(db, album, admin, form),
        admin=admin,
        headers=headers,
    )


def _grid(
    request: Request,
    db: Session,
    album: Album,
    admin: Any,
    *,
    headers: dict[str, str] | None = None,
) -> HTMLResponse:
    return render(
        request,
        "photo/_grid.html",
        _album_context(db, album, admin),
        admin=admin,
        headers=headers,
    )


def _retarget(selector: str) -> dict[str, str]:
    """Send a form's successful response somewhere other than the form itself.

    The form targets itself so a rejected save comes back with the typed text
    intact; a save that worked has to replace the surface around it.
    """
    return {"HX-Retarget": selector, "HX-Reswap": "outerHTML"}


# --------------------------------------------------------------------------
# Input handling
# --------------------------------------------------------------------------
def _parse_album(values: dict[str, str]) -> dict[str, str]:
    title = " ".join((values.get("title") or "").split())
    if not title:
        raise AlbumInvalid(translate("photo.title_required"))
    if len(title) > MAX_TITLE:
        raise AlbumInvalid(translate("photo.title_long", limit=MAX_TITLE))

    caption = (values.get("caption") or "").strip()
    if len(caption) > MAX_CAPTION:
        raise AlbumInvalid(translate("photo.caption_long", limit=MAX_CAPTION))

    return {"title": title, "caption": caption}


def _new_form(values: dict[str, str] | None = None, error: str | None = None) -> dict[str, Any]:
    return {
        "dom_id": "album-form",
        "action": "/photo/admin/albums",
        "heading": translate("photo.new_album_heading"),
        "submit": translate("photo.create_album"),
        "values": values or {"title": "", "caption": ""},
        "error": error,
        "cancel_url": "/photo/admin/board",
        "cancel_target": "#album-board",
    }


def _edit_form(
    album: Album, values: dict[str, str] | None = None, error: str | None = None
) -> dict[str, Any]:
    return {
        "dom_id": f"album-form-{album.id}",
        "action": f"/photo/admin/albums/{album.id}",
        "heading": translate("photo.edit_album"),
        "submit": translate("photo.save"),
        "values": values or {"title": album.title, "caption": album.caption},
        "error": error,
        "cancel_url": f"/photo/admin/albums/{album.id}/head",
        "cancel_target": "#album-head",
    }


def _form_response(
    request: Request, admin: Any, form: dict[str, Any], context: dict[str, Any]
) -> HTMLResponse:
    """Re-render a form with its error, keeping everything that was typed.

    Deliberately a 200: htmx does not swap error responses, and swapping the
    form back in is exactly how the typed content survives a rejected save.

    `form` is spread last on purpose — the surrounding context carries its own
    `form` key (empty on the normal path), and letting it win would blank the
    very form this function exists to re-render.
    """
    return render(
        request,
        "photo/_album_form.html",
        {**context, "form": form},
        admin=admin,
        headers=toast_headers(form["error"], "error"),
    )


# --------------------------------------------------------------------------
# The pipeline
# --------------------------------------------------------------------------
def _assign_renditions(photo: Photo, stored: images.StoredImage) -> None:
    """Map whatever renditions were produced onto the three path columns.

    A 3000px original yields 640/1600/2560; an 800px one yields only 640; a
    500px one yields a single rendition at its own width, because nothing is
    ever upscaled. Every case still has to leave a servable thumbnail.
    """
    ordered = [stored.derivatives[width] for width in sorted(stored.derivatives)]
    photo.thumb_path = ordered[0]
    photo.medium_path = ordered[1] if len(ordered) > 1 else ordered[0]
    photo.large_path = ordered[-1]
    photo.width = stored.width
    photo.height = stored.height
    photo.byte_size = stored.byte_size


def _fail(db: Session, photo: Photo, message: str) -> None:
    photo.status = PhotoStatus.FAILED
    photo.error = message
    db.add(photo)
    db.commit()


def _ensure_cover(db: Session, photo: Photo) -> None:
    """The first photo to become ready becomes the album's cover by default."""
    album = db.get(Album, photo.album_id)
    if album is not None and album.cover_photo_id is None:
        album.cover_photo_id = photo.id
        db.add(album)
        db.commit()


def process_photo(db: Session, photo_id: int) -> None:
    """Render one photo's derivatives. Runs in the background pool."""
    photo = db.get(Photo, photo_id)
    if photo is None:
        return

    photo.status = PhotoStatus.PROCESSING
    photo.error = None
    db.add(photo)
    db.commit()

    try:
        stored = images.generate_derivatives(photo.original_path, profile=images.PHOTO)
    except (FileNotFoundError, OSError) as exc:
        # A missing original is a different problem from a bad one: say which.
        missing = isinstance(exc, FileNotFoundError)
        logger.warning("photo %s could not be processed: %s", photo_id, exc)
        _fail(
            db,
            photo,
            translate("photo.original_missing" if missing else "photo.processing_failed"),
        )
        return
    except Exception:
        logger.exception("photo %s could not be processed", photo_id)
        _fail(db, photo, translate("photo.processing_failed"))
        return

    _assign_renditions(photo, stored)
    photo.status = PhotoStatus.READY
    photo.error = None
    db.add(photo)

    # Hashed from the file rather than carried down from the request: retry and
    # startup recovery reach this function without the bytes, and the digest has
    # to mean the same thing however the photo got here.
    images.record_asset(
        db,
        images.file_digest(settings.originals_dir / photo.original_path),
        stored,
    )
    db.commit()

    _ensure_cover(db, photo)


def recover_stuck_photos() -> None:
    """Startup sweep for photos a restart caught mid-pipeline (F27).

    Anything whose original survived goes back into the queue; anything whose
    original is gone is marked failed so the owner sees a retry action rather
    than a tile that spins forever.
    """
    db = SessionLocal()
    try:
        stuck = list(db.scalars(select(Photo).where(Photo.status.in_(IN_FLIGHT))))
        requeue: list[int] = []

        for photo in stuck:
            if (settings.originals_dir / photo.original_path).is_file():
                photo.status = PhotoStatus.PENDING
                photo.error = None
                requeue.append(photo.id)
            else:
                photo.status = PhotoStatus.FAILED
                photo.error = translate("photo.original_missing")
            db.add(photo)

        if stuck:
            db.commit()
            logger.info("recovered %s photo(s) left mid-processing", len(stuck))
    finally:
        db.close()

    for photo_id in requeue:
        background.submit_with_session(process_photo, photo_id)


background.register_recovery(recover_stuck_photos)


# --------------------------------------------------------------------------
# Files on disk
# --------------------------------------------------------------------------
def _files_of(photo: Photo) -> list[str | None]:
    return [photo.original_path, photo.thumb_path, photo.medium_path, photo.large_path]


# --------------------------------------------------------------------------
# Ordering
# --------------------------------------------------------------------------
def _renumber(db: Session, ordered: list[Any]) -> None:
    for position, row in enumerate(ordered):
        if row.sort_order != position:
            row.sort_order = position
            db.add(row)
    db.commit()


def _reorder_from_ids(db: Session, rows: list[Any], wanted: str) -> None:
    """Apply the order produced by dragging: a comma-separated list of ids."""
    ids = [int(part) for part in wanted.split(",") if part.strip().isdigit()]
    remaining = {row.id: row for row in rows}

    ordered: list[Any] = []
    for row_id in ids:
        row = remaining.pop(row_id, None)
        if row is not None:
            ordered.append(row)
    # Anything the client did not mention keeps its relative place at the end.
    ordered.extend(remaining.values())

    _renumber(db, ordered)


def _swap(db: Session, rows: list[Any], row: Any, direction: str) -> str:
    """Move `row` one place among `rows`. Returns "moved", "first" or "last".

    The end of the list is no longer a silent no-op. The move buttons are never
    disabled (ADR-016), so the caller turns "first"/"last" into the message that
    says why the board did not change — without it the owner cannot tell a
    refused move from a failed request. `direction` only ever arrives from
    `hx-vals`; anything else is a malformed request and answers as an end.
    """
    up = direction == "up"
    index = rows.index(row)
    target = index - 1 if up else index + 1
    if direction in ("up", "down") and 0 <= target < len(rows):
        rows[index], rows[target] = rows[target], rows[index]
        _renumber(db, rows)
        return "moved"
    return "first" if up else "last"


def _move_headers(outcome: str, kind: str) -> dict[str, str]:
    """Headers for a reorder, including the one that could not happen.

    `kind` is "album" or "photo"; the catalogue carries both the success and the
    two refusals, because no Russian belongs in a router (ADR-007).
    """
    if outcome == "moved":
        return toast_headers(translate(f"photo.{kind}s_reordered"))
    return toast_headers(translate(f"photo.{kind}_already_{outcome}"), "info")


# ==========================================================================
# Public pages
# ==========================================================================
@router.get("", response_class=HTMLResponse)
def album_index(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    return render(request, "photo/index.html", _index_context(db, admin), admin=admin)


# ==========================================================================
# Admin — albums
# ==========================================================================
@router.get("/admin/board", response_class=HTMLResponse)
def album_board(request: Request, db: DbSession, admin: CurrentAdmin) -> HTMLResponse:
    """The index with no form open — what «Отмена» returns to."""
    return _board(request, db, admin)


@router.get("/admin/new", response_class=HTMLResponse)
def album_new(request: Request, db: DbSession, admin: CurrentAdmin) -> HTMLResponse:
    return _board(request, db, admin, form=_new_form())


@router.post("/admin/albums", response_class=HTMLResponse)
def album_create(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    title: str = Form(""),
    caption: str = Form(""),
) -> HTMLResponse:
    submitted = {"title": title, "caption": caption}
    try:
        fields = _parse_album(submitted)
    except AlbumInvalid as exc:
        return _form_response(
            request, admin, _new_form(submitted, str(exc)), _index_context(db, admin)
        )

    last = db.scalar(select(func.max(Album.sort_order)))
    album = Album(
        slug=unique_slug(db, Album, fields["title"]),
        is_published=False,
        sort_order=(last or 0) + 1,
        **fields,
    )
    db.add(album)
    db.commit()

    # Straight into the new album: the next thing the owner wants is the drop
    # zone, not the index they just left.
    return Response(
        status_code=200,
        headers={"HX-Redirect": f"/photo/{album.slug}"}
        | toast_headers(translate("photo.album_created")),
    )


@router.get("/admin/albums/{album_id}/head", response_class=HTMLResponse)
def album_head(request: Request, db: DbSession, admin: CurrentAdmin, album_id: int) -> HTMLResponse:
    """The album's header with no form open — what «Отмена» returns to."""
    return _head(request, db, _get_album(db, album_id), admin)


@router.get("/admin/albums/{album_id}/edit", response_class=HTMLResponse)
def album_edit(request: Request, db: DbSession, admin: CurrentAdmin, album_id: int) -> HTMLResponse:
    album = _get_album(db, album_id)
    return _head(request, db, album, admin, form=_edit_form(album))


@router.post("/admin/albums/{album_id}", response_class=HTMLResponse)
def album_update(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    album_id: int,
    title: str = Form(""),
    caption: str = Form(""),
) -> HTMLResponse:
    album = _get_album(db, album_id)
    submitted = {"title": title, "caption": caption}
    try:
        fields = _parse_album(submitted)
    except AlbumInvalid as exc:
        return _form_response(
            request,
            admin,
            _edit_form(album, submitted, str(exc)),
            _album_context(db, album, admin),
        )

    album.title = fields["title"]
    album.caption = fields["caption"]
    # A published URL stays put; a draft's slug still follows its title.
    if not album.is_published:
        album.slug = unique_slug(db, Album, fields["title"], exclude_id=album.id)
    db.add(album)
    db.commit()

    return _head(
        request,
        db,
        album,
        admin,
        headers=toast_headers(translate("photo.album_saved")) | _retarget("#album-head"),
    )


@router.post("/admin/albums/{album_id}/publish", response_class=HTMLResponse)
def album_publish(
    request: Request, db: DbSession, admin: CurrentAdmin, album_id: int
) -> HTMLResponse:
    album = _get_album(db, album_id)
    album.is_published = not album.is_published
    db.add(album)
    db.commit()

    key = "photo.album_published" if album.is_published else "photo.album_unpublished"
    return _head(request, db, album, admin, headers=toast_headers(translate(key)))


@router.post("/admin/albums/{album_id}/move", response_class=HTMLResponse)
def album_move(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    album_id: int,
    direction: str = Form(""),
    view: str = Form("index"),
    title: str | None = Form(None),
    caption: str | None = Form(None),
) -> HTMLResponse:
    """Keyboard-accessible reordering: the alternative to dragging.

    Reachable from both surfaces that show an album's position, so `view` says
    which one to render back — the index board, or the album's own header.

    From the header the buttons sit *inside* the edit form and the swap replaces
    it, so they send its fields along and the form is rebuilt from what was
    typed. Rebuilding it from the stored row instead is what made pressing ↑
    throw away an unsaved title.
    """
    album = _get_album(db, album_id)
    ordered = list(db.scalars(select(Album).order_by(Album.sort_order, Album.id)))
    headers = _move_headers(_swap(db, ordered, album, direction), "album")
    if view == "album":
        typed = None if title is None else {"title": title, "caption": caption or ""}
        return _head(request, db, album, admin, form=_edit_form(album, typed), headers=headers)
    return _board(request, db, admin, headers=headers)


@router.post("/admin/order", response_class=HTMLResponse)
def album_reorder(
    request: Request, db: DbSession, admin: CurrentAdmin, order: str = Form("")
) -> HTMLResponse:
    rows = list(db.scalars(select(Album).order_by(Album.sort_order, Album.id)))
    _reorder_from_ids(db, rows, order)
    return _board(request, db, admin, headers=toast_headers(translate("photo.albums_reordered")))


@router.delete("/admin/albums/{album_id}")
def album_delete(db: DbSession, admin: CurrentAdmin, album_id: int) -> Response:
    """Remove the album, its photos and every file the two of them own."""
    album = _get_album(db, album_id)
    doomed: list[str | None] = []
    for photo in db.scalars(select(Photo).where(Photo.album_id == album.id)):
        doomed.extend(_files_of(photo))

    # Release the cover first: the FK to `photo` would otherwise be resolved by
    # the database mid-delete rather than by us.
    album.cover_photo_id = None
    db.add(album)
    db.flush()
    db.delete(album)
    db.commit()

    # Only once the rows are gone, so a failed commit cannot orphan the page.
    # `release` keeps whatever another album or article still points at: with
    # deduplication a file is no longer owned by whoever uploaded it (F41).
    images.release(db, *doomed)

    return Response(
        status_code=200,
        headers={"HX-Redirect": "/photo"} | toast_headers(translate("photo.album_deleted")),
    )


# ==========================================================================
# Admin — photos
# ==========================================================================
@router.get("/admin/albums/{album_id}/grid", response_class=HTMLResponse)
def photo_grid(request: Request, db: DbSession, admin: CurrentAdmin, album_id: int) -> HTMLResponse:
    """What the grid polls while the pipeline still owes it thumbnails."""
    return _grid(request, db, _get_album(db, album_id), admin)


@router.post("/admin/albums/{album_id}/photos")
def photo_upload(
    db: DbSession,
    admin: CurrentAdmin,
    album_id: int,
    file: UploadFile | None = File(None),
) -> JSONResponse:
    """Accept one file from the batch uploader.

    One request per file is what makes per-file progress and per-file failure
    possible: a rejected shot reports its own reason and the rest of the batch
    never notices.
    """
    album = _get_album(db, album_id)

    if file is None or not file.filename:
        return JSONResponse({"detail": translate("photo.upload_no_file")}, status_code=422)

    in_flight = db.scalar(
        select(func.count())
        .select_from(Photo)
        .where(Photo.album_id == album.id, Photo.status.in_(IN_FLIGHT))
    )
    if (in_flight or 0) >= settings.max_batch_files:
        return JSONResponse({"detail": translate("photo.too_many_files")}, status_code=429)

    data = file.file.read()
    try:
        mime = images.validate_upload(file.filename, file.content_type, data)
    except images.ImageRejected as exc:
        return JSONResponse({"detail": str(exc)}, status_code=422)

    last = db.scalar(select(func.max(Photo.sort_order)).where(Photo.album_id == album.id))

    known = images.find_asset(db, images.content_digest(data))
    if known is not None:
        # These exact bytes are already stored (F42): no second file, whatever
        # happens next. Whether they are already *rendered* for an album is a
        # different question — a frame first uploaded as a cover carries the
        # COVER ladder, which stops at 1600 px at quality 85 and never holds the
        # frame's own width. Serving that in the lightbox forever is the one
        # thing ADR-014 says must not happen, so the missing rungs go to the
        # pool exactly as a fresh upload would.
        photo = Photo(
            album_id=album.id,
            original_path=known.original_path,
            sort_order=(last or 0) + 1,
        )
        if images.missing_rungs(known, images.PHOTO):
            photo.status = PhotoStatus.PENDING
            db.add(photo)
            db.commit()
            background.submit_with_session(process_photo, photo.id)
        else:
            photo.status = PhotoStatus.READY
            _assign_renditions(photo, images.stored_from_asset(known))
            db.add(photo)
            db.commit()
            _ensure_cover(db, photo)
        return JSONResponse({"id": photo.id, "status": photo.status.value}, status_code=201)

    relative: str | None = None
    try:
        relative, absolute = images.store_original(
            data, mime, kind=PHOTO_KIND, group=images.group_name(album.id, album.slug)
        )
        images.verify_decodable(absolute)
    except images.ImageRejected as exc:
        # Nothing half-written survives a rejection.
        images.delete_files(relative)
        return JSONResponse({"detail": str(exc)}, status_code=422)

    photo = Photo(
        album_id=album.id,
        original_path=relative,
        byte_size=len(data),
        status=PhotoStatus.PENDING,
        sort_order=(last or 0) + 1,
    )
    db.add(photo)
    db.commit()

    # Rendering four WebP sizes of a 50 MB frame does not belong on the
    # request path; the grid picks the result up by polling.
    background.submit_with_session(process_photo, photo.id)

    return JSONResponse({"id": photo.id, "status": photo.status.value}, status_code=201)


@router.post("/admin/photos/{photo_id}/alt", response_class=HTMLResponse)
def photo_alt_save(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    photo_id: int,
    alt: str = Form(""),
) -> HTMLResponse:
    photo = _get_photo(db, photo_id)
    photo.alt = " ".join((alt or "").split())[:MAX_ALT]
    db.add(photo)
    db.commit()

    album = _get_album(db, photo.album_id)
    return render(
        request,
        "photo/_photo_tile.html",
        {"photo": photo, "album": album, **_helpers()},
        admin=admin,
        headers=toast_headers(translate("photo.alt_saved")),
    )


@router.post("/admin/photos/{photo_id}/cover", response_class=HTMLResponse)
def photo_set_cover(
    request: Request, db: DbSession, admin: CurrentAdmin, photo_id: int
) -> HTMLResponse:
    photo = _get_photo(db, photo_id)
    album = _get_album(db, photo.album_id)

    # The ★ button is rendered for the current cover too, so that pressing it
    # cannot delete the element htmx restores focus to (ADR-016). Pressing it
    # there is a no-op that says so rather than a swap that says nothing.
    if album.cover_photo_id == photo.id:
        headers = toast_headers(translate("photo.already_cover"), "info")
        return _grid(request, db, album, admin, headers=headers)

    album.cover_photo_id = photo.id
    db.add(album)
    db.commit()

    return _grid(request, db, album, admin, headers=toast_headers(translate("photo.cover_set")))


@router.post("/admin/photos/{photo_id}/retry", response_class=HTMLResponse)
def photo_retry(
    request: Request, db: DbSession, admin: CurrentAdmin, photo_id: int
) -> HTMLResponse:
    """Put a failed photo back into the queue (F27's retry action)."""
    photo = _get_photo(db, photo_id)
    photo.status = PhotoStatus.PENDING
    photo.error = None
    db.add(photo)
    db.commit()

    background.submit_with_session(process_photo, photo.id)

    album = _get_album(db, photo.album_id)
    return _grid(request, db, album, admin, headers=toast_headers(translate("photo.retry_started")))


@router.post("/admin/photos/{photo_id}/move", response_class=HTMLResponse)
def photo_move(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    photo_id: int,
    direction: str = Form(""),
) -> HTMLResponse:
    photo = _get_photo(db, photo_id)
    album = _get_album(db, photo.album_id)
    ordered = list(
        db.scalars(
            select(Photo).where(Photo.album_id == album.id).order_by(Photo.sort_order, Photo.id)
        )
    )
    outcome = _swap(db, ordered, photo, direction)

    return _grid(request, db, album, admin, headers=_move_headers(outcome, "photo"))


@router.post("/admin/albums/{album_id}/photo-order", response_class=HTMLResponse)
def photo_reorder(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    album_id: int,
    order: str = Form(""),
) -> HTMLResponse:
    album = _get_album(db, album_id)
    rows = list(
        db.scalars(
            select(Photo).where(Photo.album_id == album.id).order_by(Photo.sort_order, Photo.id)
        )
    )
    _reorder_from_ids(db, rows, order)
    return _grid(
        request, db, album, admin, headers=toast_headers(translate("photo.photos_reordered"))
    )


@router.delete("/admin/photos/{photo_id}", response_class=HTMLResponse)
def photo_delete(
    request: Request, db: DbSession, admin: CurrentAdmin, photo_id: int
) -> HTMLResponse:
    photo = _get_photo(db, photo_id)
    album = _get_album(db, photo.album_id)
    doomed = _files_of(photo)
    was_cover = album.cover_photo_id == photo.id

    db.delete(photo)
    db.commit()

    if was_cover:
        # The FK clears itself; choosing the replacement is ours to do.
        replacement = db.scalar(
            select(Photo)
            .where(Photo.album_id == album.id, Photo.status == PhotoStatus.READY)
            .order_by(Photo.sort_order, Photo.id)
        )
        album.cover_photo_id = replacement.id if replacement else None
        db.add(album)
        db.commit()

    # Only once the row is gone, so a failed commit cannot orphan the page.
    # `release` keeps a file the same frame elsewhere still uses (F41).
    images.release(db, *doomed)

    return _grid(request, db, album, admin, headers=toast_headers(translate("photo.photo_deleted")))


# ==========================================================================
# Album page — registered last so /photo/admin/… can never be read as a slug
# ==========================================================================
@router.get("/{slug}", response_class=HTMLResponse)
def album_detail(request: Request, db: DbSession, admin: OptionalAdmin, slug: str) -> HTMLResponse:
    album = db.scalar(select(Album).where(Album.slug == slug))
    if album is None or (admin is None and not album.is_published):
        raise HTTPException(status_code=404, detail=translate("photo.not_found"))

    context = _album_context(db, album, admin)
    cover = album.cover_photo
    return render(
        request,
        "photo/album.html",
        {
            **context,
            "meta_description": album.caption or translate("photo.lede"),
            "og_image": display_src(cover) if cover else None,
        },
        admin=admin,
    )
