"""Home page and the editable site-copy blocks it is built from."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from app.deps import CurrentAdmin, DbSession, OptionalAdmin
from app.models.site_content import SiteContent
from app.services.markdown import render_markdown
from app.templating import render, toast_headers, translate

router = APIRouter()

# Blocks the owner can edit in place, with the copy shipped as a starting point.
CONTENT_KEYS = {
    "home.intro": "home.intro_default",
}


def _get_block(db: DbSession, key: str) -> SiteContent:
    """Fetch a copy block, seeding it from the bundled default the first time."""
    block = db.get(SiteContent, (key, "ru"))
    if block is None:
        default_md = translate(CONTENT_KEYS.get(key, key))
        block = SiteContent(
            key=key,
            lang="ru",
            value_md=default_md,
            value_html=render_markdown(default_md),
        )
        db.add(block)
        db.commit()
        db.refresh(block)
    return block


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    hero = translate("home.hero_default")
    intro = _get_block(db, "home.intro")
    return render(
        request,
        "pages/home.html",
        {
            "active_section": "home",
            "hero_lines": [line for line in hero.split("\n") if line.strip()],
            "intro_key": "home.intro",
            "intro_html": intro.value_html,
        },
        admin=admin,
    )


# --------------------------------------------------------------------------
# In-place editing of site copy
# --------------------------------------------------------------------------
@router.get("/admin/content/{key}", response_class=HTMLResponse)
def content_view(request: Request, db: DbSession, admin: CurrentAdmin, key: str) -> HTMLResponse:
    block = _get_block(db, key)
    return render(
        request,
        "partials/editable.html",
        {"key": key, "html": block.value_html},
        admin=admin,
    )


@router.get("/admin/content/{key}/edit", response_class=HTMLResponse)
def content_edit(request: Request, db: DbSession, admin: CurrentAdmin, key: str) -> HTMLResponse:
    block = _get_block(db, key)
    return render(
        request,
        "partials/editable_form.html",
        {"key": key, "value_md": block.value_md},
        admin=admin,
    )


@router.post("/admin/content/{key}", response_class=HTMLResponse)
def content_save(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    key: str,
    value_md: str = Form(""),
) -> HTMLResponse:
    block = _get_block(db, key)
    block.value_md = value_md
    block.value_html = render_markdown(value_md)
    db.add(block)
    db.commit()
    return render(
        request,
        "partials/editable.html",
        {"key": key, "html": block.value_html},
        admin=admin,
        headers=toast_headers("Сохранено"),
    )
