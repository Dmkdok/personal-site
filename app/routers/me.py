"""The cabinet — the owner's private rooms (F62, F64).

Everything on it is a read the other routers already do, gathered onto one screen
and linked back to the page that edits it. Nothing is authored here: the published
page and the editing page stay the same page (ADR-001), and the only action in the
whole cabinet is the retry a failed photograph's own tile already posts to.

The gap it closes is state that is not on the page you are looking at — a draft is
visible only on `/blog`, an unpublished album only on `/photo`, a photograph that
failed to process only inside its own album. ADR-025 declined to build a notifier
for exactly that and named the log file as the substitute, which requires knowing
something went wrong first.

Three rooms, each its own address (ADR-036): «События» at `/me` is F62's list,
«Сводка» at `/me/stats` says how much there is of everything, and «Медиа» at
`/me/media` shows photographs still in flight and, on request, the files on disk
nothing points at. Photographs with no description are deliberately **not** here:
on real data that section was two dozen rows all reading «Снимок в альбоме «X»»,
and the prompt belongs in the album, in «Правка», at the moment the owner is
looking at the picture.
"""

from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.deps import DbSession, OptionalAdmin
from app.models.album import Album
from app.models.media_asset import MediaAsset
from app.models.photo import Photo, PhotoStatus
from app.models.post import Post, PostStatus
from app.models.project import Project
from app.routers.blog import ru_date
from app.services import storage
from app.templating import render, translate

router = APIRouter(include_in_schema=False)

IN_FLIGHT = (PhotoStatus.PENDING, PhotoStatus.PROCESSING)


@dataclass(frozen=True)
class Item:
    """One thing waiting, and the page that deals with it."""

    url: str
    title: str
    note: str = ""
    #: Set only for a photograph that failed to process: it carries the retry
    #: `_photo_tile.html` already posts to. Everything else on the page is a
    #: link, because everything else is edited where it lives.
    retry_photo_id: int | None = None


@dataclass(frozen=True)
class Group:
    """One section. `key` names both its heading and its i18n key."""

    key: str
    items: list[Item]


@dataclass(frozen=True)
class Figure:
    """One number in «Сводка». `key` names it; `value` is already formatted."""

    key: str
    value: str | int


@dataclass(frozen=True)
class Panel:
    """A handful of figures under one heading."""

    key: str
    figures: list[Figure]


@dataclass(frozen=True)
class Orphan:
    """One upload on disk nothing on the site points at, as the page shows it."""

    stem: str
    files: int
    size: str


def _require_owner(admin: OptionalAdmin) -> None:
    """404 to anyone without a session — no room confirms it is there.

    Deliberately not `CurrentAdmin`, which answers 401 and is turned into a
    redirect to `/login` by the handler in `main.py`: a redirect tells a stranger
    the page exists. A draft article gets exactly this treatment (ADR-029), which
    is also why `test_authz_sweep.py`'s parametrized admin-read case — it asserts
    redirect-to-login semantics — does not cover these routes and must not be
    made to.

    Written once and called by every room, so a fourth room cannot be added
    without it.
    """
    if admin is None:
        raise HTTPException(status_code=404)


def _photo_item(photo: Photo, *, retry: bool) -> Item:
    """A photograph, named by the album it is in — a photograph has no title.

    The fragment lands the owner on the tile itself: `_photo_tile.html` gives
    every one an `id`, and the album page is where a description is typed and a
    retry is pressed.
    """
    return Item(
        url=f"/photo/{photo.album.slug}#photo-{photo.id}",
        title=translate("me.photo_in", album=photo.album.title),
        note=photo.error or "",
        retry_photo_id=photo.id if retry else None,
    )


def _photos(db: DbSession, *where) -> list[Photo]:
    """`selectinload`: every list names its album, and without it one query per
    photograph goes back for the same handful of albums."""
    return list(
        db.scalars(
            select(Photo)
            .where(*where)
            .options(selectinload(Photo.album))
            .order_by(Photo.created_at.desc())
        ).all()
    )


def _count(db: DbSession, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def _megabytes(size: int) -> str:
    """Bytes as «12,4», one unit for the whole page.

    `scripts/media_orphans.py` keeps its own B/KB/MB/GB ladder: its output is a
    terminal's and had to stay identical to the byte (ADR-037). This is the
    Russian page's form — one unit, a decimal comma — and it is a formatting
    choice at the edge, not a second answer about what is on disk.
    """
    return f"{size / 1024 / 1024:.1f}".replace(".", ",")


def _failed_group(db: DbSession) -> Group:
    """Shared by «События» and «Медиа»: the same list with the same retry.

    Both rooms genuinely want it — a failed photograph is something waiting *and*
    something wrong with the media pipeline — and one function means the two
    cannot end up listing it differently.
    """
    failed = _photos(db, Photo.status == PhotoStatus.FAILED)
    return Group("failed", [_photo_item(photo, retry=True) for photo in failed])


@router.get("/me", response_class=HTMLResponse)
def cabinet(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    """«События» — what is waiting, and where it is dealt with (F62)."""
    _require_owner(admin)

    drafts = db.scalars(
        select(Post).where(Post.status == PostStatus.DRAFT).order_by(Post.updated_at.desc())
    ).all()
    albums = db.scalars(
        select(Album).where(Album.is_published.is_(False)).order_by(Album.sort_order, Album.id)
    ).all()
    projects = db.scalars(
        select(Project)
        .where(Project.is_published.is_(False))
        .order_by(Project.sort_order, Project.id)
    ).all()

    groups = [
        Group("drafts", [Item(f"/blog/{p.slug}/edit", p.title) for p in drafts]),
        Group("albums", [Item(f"/photo/{a.slug}", a.title) for a in albums]),
        # The board, not `/dev/{slug}`: a project with no long description has
        # no page of its own and answers 404 even to the owner, and the board is
        # where a project is published and reordered anyway.
        Group("projects", [Item(f"/dev#project-{p.id}", p.title) for p in projects]),
        _failed_group(db),
    ]

    return render(
        request,
        "pages/me.html",
        {"room": "events", "groups": [group for group in groups if group.items]},
        admin=admin,
    )


@router.get("/me/stats", response_class=HTMLResponse)
def stats(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    """«Сводка» — how much there is of everything, and when the last thing went out.

    Every figure is a count over rows that already exist: no new model, no
    migration, no column that could drift out of step with what it counts.
    """
    _require_owner(admin)

    stored = db.scalar(select(func.coalesce(func.sum(MediaAsset.byte_size), 0))) or 0
    # Only articles carry a publication date — an album and a project have a
    # published flag and nothing else — so this is the last article, and the
    # figure is named for that rather than for publishing in general.
    latest: datetime | None = db.scalar(
        select(func.max(Post.published_at)).where(Post.status == PostStatus.PUBLISHED)
    )

    panels = [
        Panel(
            "content",
            [
                Figure("posts_published", _count(db, Post, Post.status == PostStatus.PUBLISHED)),
                Figure("posts_draft", _count(db, Post, Post.status == PostStatus.DRAFT)),
                Figure("albums_published", _count(db, Album, Album.is_published.is_(True))),
                Figure("albums_hidden", _count(db, Album, Album.is_published.is_(False))),
                Figure("projects_published", _count(db, Project, Project.is_published.is_(True))),
                Figure("projects_hidden", _count(db, Project, Project.is_published.is_(False))),
            ],
        ),
        Panel(
            "photos",
            [
                Figure(f"photos_{status.value}", _count(db, Photo, Photo.status == status))
                for status in PhotoStatus
            ],
        ),
        Panel(
            "storage",
            [
                Figure("uploads", _count(db, MediaAsset)),
                Figure("stored", translate("me.megabytes", value=_megabytes(stored))),
                Figure("last_post", ru_date(latest) if latest else translate("me.never")),
            ],
        ),
    ]

    return render(request, "pages/me_stats.html", {"room": "stats", "panels": panels}, admin=admin)


@router.get("/me/media", response_class=HTMLResponse)
def media(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    """«Медиа» — the pipeline, from the database only (ADR-037).

    The disk is not walked here. This page must stay usable at the moment
    something is wrong with the storage it describes, so the walk is behind
    «Проверить» and answers into its own region.
    """
    _require_owner(admin)

    in_flight = _photos(db, Photo.status.in_(IN_FLIGHT))
    groups = [
        Group("in_flight", [_photo_item(photo, retry=False) for photo in in_flight]),
        _failed_group(db),
    ]

    return render(
        request,
        "pages/me_media.html",
        {"room": "media", "groups": [group for group in groups if group.items]},
        admin=admin,
    )


@router.get("/me/media/orphans", response_class=HTMLResponse)
def media_orphans(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    """The disk walk, on a press — a read, and the only thing on it (ADR-037).

    The same `storage.scan` `scripts/media_orphans.py` prints, so the number here
    and the number the command reports cannot disagree. Nothing on this page
    deletes a file: pruning stays a deliberate command on the server, where the
    owner can read what will go before it goes.
    """
    _require_owner(admin)

    disk = storage.scan(db)
    return render(
        request,
        "partials/orphan_scan.html",
        {
            "files": disk.file_count,
            "uploads": len(disk.uploads),
            "orphans": [
                Orphan(stem=upload.stem, files=len(upload.files), size=_megabytes(upload.byte_size))
                for upload in disk.orphans
            ],
            "orphan_size": _megabytes(disk.orphan_bytes),
            "shared": disk.shared,
            "empty": [
                path.relative_to(settings.media_root).as_posix()
                for path in storage.empty_directories()
            ],
        },
        admin=admin,
    )
