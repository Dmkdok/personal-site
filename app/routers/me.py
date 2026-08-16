"""The cabinet — the one private page that says what needs the owner (F62).

Everything on it is a read the other routers already do, gathered onto one
screen and linked back to the page that edits it. Nothing is authored here: the
published page and the editing page stay the same page (ADR-001), and the only
action on this one is the retry a failed photograph's own tile already posts to.

The gap it closes is state that is not on the page you are looking at — a draft
is visible only on `/blog`, an unpublished album only on `/photo`, a photograph
nobody described only inside its own album. ADR-025 declined to build a
notifier for exactly that and named the log file as the substitute, which
requires knowing something went wrong first.
"""

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import DbSession, OptionalAdmin
from app.models.album import Album
from app.models.photo import Photo, PhotoStatus
from app.models.post import Post, PostStatus
from app.models.project import Project
from app.templating import render, translate

router = APIRouter(include_in_schema=False)


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


@router.get("/me", response_class=HTMLResponse)
def cabinet(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    """404 to anyone without a session — the address does not confirm itself.

    Deliberately not `CurrentAdmin`, which answers 401 and is turned into a
    redirect to `/login` by the handler in `main.py`: a redirect tells a
    stranger the page is there. A draft article gets exactly this treatment
    (ADR-029), which is also why `test_authz_sweep.py`'s parametrized
    admin-read case — it asserts redirect-to-login semantics — does not cover
    this route and must not be made to.
    """
    if admin is None:
        raise HTTPException(status_code=404)

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

    # `selectinload`: both photo lists name their album, and without it one
    # query per photograph goes back for the same handful of albums.
    failed = db.scalars(
        select(Photo)
        .where(Photo.status == PhotoStatus.FAILED)
        .options(selectinload(Photo.album))
        .order_by(Photo.created_at.desc())
    ).all()
    # `READY` only: a photograph that never finished processing is already in
    # the list above, and asking for a description of it is asking twice about
    # the same problem.
    undescribed = db.scalars(
        select(Photo)
        .where(Photo.alt == "", Photo.status == PhotoStatus.READY)
        .options(selectinload(Photo.album))
        .order_by(Photo.created_at.desc())
    ).all()

    groups = [
        Group("drafts", [Item(f"/blog/{p.slug}/edit", p.title) for p in drafts]),
        Group("albums", [Item(f"/photo/{a.slug}", a.title) for a in albums]),
        # The board, not `/dev/{slug}`: a project with no long description has
        # no page of its own and answers 404 even to the owner, and the board is
        # where a project is published and reordered anyway.
        Group("projects", [Item(f"/dev#project-{p.id}", p.title) for p in projects]),
        Group("failed", [_photo_item(photo, retry=True) for photo in failed]),
        Group("undescribed", [_photo_item(photo, retry=False) for photo in undescribed]),
    ]

    return render(
        request,
        "pages/me.html",
        {"groups": [group for group in groups if group.items]},
        admin=admin,
    )
