"""Shared articles: private, reachable only by their own secret link (F67).

A shared article is not a blog draft — it has no status, slug or place in the
blog's own lifecycle (ADR-042). A friend reaches one only through
`GET /s/{share_token}`; the owner writes and manages them from `/me/shared`,
one more room in the cabinet (F64), using `_require_owner` from
`app.routers.me` so a visitor's request behaves exactly like every other room:
a plain 404, never a redirect that would confirm the room exists.

The public route accepts nothing but the token itself and never mutates
anything (F68). Every route that writes — create, save, delete, regenerate,
and the editor's own preview — is `CurrentAdmin`, the same guard every other
mutating endpoint in the application uses, with no exceptions. There is
deliberately no rate limiter here (ADR-043): the 256-bit token is the whole
defence. Image upload is out of scope this round — title and Markdown body
only.
"""

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.deps import CurrentAdmin, DbSession, OptionalAdmin
from app.models.shared_article import SharedArticle
from app.routers.me import _require_owner
from app.services.markdown import render_markdown
from app.templating import render, toast_headers, translate

router = APIRouter(tags=["shared"])


def _now_hm() -> str:
    return datetime.now(UTC).strftime("%H:%M")


def _get_article(db: DbSession, id: int) -> SharedArticle:
    article = db.get(SharedArticle, id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=translate("shared.not_found")
        )
    return article


# --------------------------------------------------------------------------
# The public link (F67, F69) — no admin dependency at all, so the page an
# owner sees through their own link is byte-for-byte what a friend sees.
# --------------------------------------------------------------------------
@router.get("/s/{share_token}", response_class=HTMLResponse)
def read_shared_article(request: Request, db: DbSession, share_token: str) -> HTMLResponse:
    article = db.scalar(select(SharedArticle).where(SharedArticle.share_token == share_token))
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=translate("shared.not_found")
        )
    return render(request, "pages/shared_article.html", {"article": article})


# --------------------------------------------------------------------------
# The cabinet room (F70)
# --------------------------------------------------------------------------
@router.get("/me/shared", response_class=HTMLResponse)
def shared_list(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    _require_owner(admin)

    articles = db.scalars(select(SharedArticle).order_by(SharedArticle.updated_at.desc())).all()
    return render(
        request, "pages/me_shared.html", {"room": "shared", "articles": articles}, admin=admin
    )


@router.post("/me/shared")
def create_shared_article(db: DbSession, admin: CurrentAdmin, title: str = Form("")) -> Response:
    """Create the article and hand the owner straight to its editor."""
    clean_title = title.strip()[:250] or translate("shared.untitled")
    article = SharedArticle(title=clean_title, body_md="", body_html="")
    db.add(article)
    db.commit()
    db.refresh(article)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={
            "HX-Redirect": f"/me/shared/{article.id}/edit",
            **toast_headers(translate("shared.toast_created")),
        },
    )


# --------------------------------------------------------------------------
# The editor (F70) — full Markdown editing with a live preview built from the
# exact same call the public page renders with, so the two cannot drift.
# --------------------------------------------------------------------------
@router.get("/me/shared/{id}/edit", response_class=HTMLResponse)
def shared_editor(request: Request, db: DbSession, admin: CurrentAdmin, id: int) -> HTMLResponse:
    article = _get_article(db, id)
    return render(
        request,
        "pages/shared_editor.html",
        {"article": article, "saved_label": None},
        admin=admin,
    )


@router.post("/me/shared/preview", response_class=HTMLResponse)
def preview(admin: CurrentAdmin, body_md: str = Form("")) -> HTMLResponse:
    """The live preview.

    Deliberately the same call the published page is built from, so the two
    cannot drift apart (F67).
    """
    return HTMLResponse(render_markdown(body_md))


@router.post("/me/shared/{id}/save", response_class=HTMLResponse)
def save_shared_article(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    id: int,
    title: str = Form(""),
    body_md: str = Form(""),
) -> HTMLResponse:
    article = _get_article(db, id)
    article.title = title.strip()[:250] or translate("shared.untitled")
    article.body_md = body_md
    article.body_html = render_markdown(body_md)
    db.add(article)
    db.commit()
    db.refresh(article)

    return render(
        request,
        "partials/shared_save_state.html",
        {"article": article, "saved_label": translate("shared.saved_at", time=_now_hm())},
        admin=admin,
    )


@router.post("/me/shared/{id}/regenerate", response_class=HTMLResponse)
def regenerate_token(request: Request, db: DbSession, admin: CurrentAdmin, id: int) -> HTMLResponse:
    """A fresh token (F71) — the old one 404s from this request onward."""
    article = _get_article(db, id)
    article.share_token = secrets.token_urlsafe(32)
    db.add(article)
    db.commit()
    db.refresh(article)

    return render(
        request,
        "partials/shared_link.html",
        {"article": article},
        admin=admin,
        headers=toast_headers(translate("shared.toast_regenerated")),
    )


@router.post("/me/shared/{id}/delete")
def delete_shared_article(db: DbSession, admin: CurrentAdmin, id: int) -> Response:
    article = _get_article(db, id)
    db.delete(article)
    db.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"HX-Redirect": "/me/shared", **toast_headers(translate("shared.toast_deleted"))},
    )
