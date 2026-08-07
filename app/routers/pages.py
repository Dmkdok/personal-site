"""Home page, the editable site-copy blocks, and the owner's outbound links."""

from collections.abc import Collection
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.deps import CurrentAdmin, DbSession, OptionalAdmin
from app.models.site_content import SiteContent
from app.services.markdown import render_markdown
from app.templating import render, templates, toast_headers, translate

router = APIRouter()

#: The owner's outbound links, in the order they render. One row per slug in
#: `site_content`, shown twice: as the footer list and as the home page's chips.
LINK_SLUGS = ("github", "telegram", "vk", "youtube")

LINK_KEYS = tuple(f"footer.{slug}" for slug in LINK_SLUGS)
RIGHTS_KEY = "footer.rights"

# Blocks the owner can edit in place, with the copy shipped as a starting point.
CONTENT_KEYS = {
    "home.intro": "home.intro_default",
    RIGHTS_KEY: RIGHTS_KEY,
    **{key: f"{key}_default" for key in LINK_KEYS},
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


# ---------------------------------------------------------------- site links
# The four social links and the name in the copyright line used to be typed
# into two templates, so changing one meant editing both. They are ordinary
# `SiteContent` rows now — same storage as the editable copy above — rendered
# by `partials/site_links.html` in the footer and `partials/site_contacts.html`
# on the home page.

#: Anything outside this can never reach an href. A whitelist, because
#: `javascript:` and `data:` are exactly what a blacklist forgets.
ALLOWED_SCHEMES = frozenset({"http", "https"})


def _clean_url(raw: str) -> str | None:
    """Vet a submitted link.

    Returns the trimmed URL, `""` for «no link here», or `None` when the value
    is not an http(s) URL and the submission must be refused.
    """
    value = raw.strip()
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES or not parsed.netloc:
        return None
    return value


def _link_values(db: Session) -> dict[str, str]:
    """Stored value per key, falling back to the bundled default.

    Deliberately does not seed rows the way `_get_block` does: this runs while
    the footer renders, on every page in the site, and a template render must
    not write to the database. A row appears the first time the owner saves.
    """
    keys = (*LINK_KEYS, RIGHTS_KEY)
    rows = db.scalars(
        select(SiteContent).where(SiteContent.key.in_(keys), SiteContent.lang == "ru")
    )
    stored = {row.key: row.value_md for row in rows}
    return {key: stored.get(key, translate(CONTENT_KEYS[key])) for key in keys}


def _site_links(db: Session) -> dict[str, Any]:
    """Template context for both renderings: the visible links and the name.

    Every URL is vetted again on the way out, so a value written straight into
    the table — bypassing the form — still cannot produce a dangerous href.
    """
    values = _link_values(db)
    links = [
        {"slug": slug, "label": translate(f"footer.{slug}_label"), "url": url}
        for slug in LINK_SLUGS
        if (url := _clean_url(values[f"footer.{slug}"]))
    ]
    return {"links": links, "rights": values[RIGHTS_KEY]}


def site_links_global() -> dict[str, Any]:
    """`site_links()` inside a template.

    The footer lives in `base.html`, so every page in the application needs
    these values. Threading them through each router's context would mean
    editing every router for one shared block, so they are fetched here instead,
    in a short-lived read-only session.
    """
    db = SessionLocal()
    try:
        return _site_links(db)
    finally:
        db.close()


templates.env.globals["site_links"] = site_links_global


def _form_context(values: dict[str, str], invalid: Collection[str] = ()) -> dict[str, Any]:
    """Fields for the edit form.

    Every id here is dot-free on purpose: the keys carry a dot (`footer.github`)
    and `#site-link-footer.github` parses as «#site-link-footer with class
    github» — the trap documented in `partials/editable.html`.
    """
    return {
        "fields": [
            {
                "name": slug,
                "dom_id": f"site-link-{slug}",
                "label": translate(f"footer.{slug}_label"),
                "value": values[f"footer.{slug}"],
                "invalid": slug in invalid,
            }
            for slug in LINK_SLUGS
        ],
        "rights": values[RIGHTS_KEY],
        "rights_label": translate("footer.rights_label"),
    }


def _put_value(db: Session, key: str, value: str) -> None:
    """Write a plain (non-Markdown) site value.

    `value_html` stays empty: a link and a name are literal text, and rendering
    them as Markdown would only invite a stray `*` into an href.
    """
    block = db.get(SiteContent, (key, "ru"))
    if block is None:
        block = SiteContent(key=key, lang="ru")
    block.value_md = value
    block.value_html = ""
    db.add(block)


def _editing_from_home(request: Request) -> bool:
    """Is the owner editing from the home page?

    The home page shows the same links as chips, and the save response carries
    an out-of-band copy of that block so both update at once. Anywhere else the
    element does not exist and htmx would log a missing-target error, so the
    fragment is only sent when it has somewhere to land.
    """
    return urlsplit(request.headers.get("HX-Current-URL", "")).path in ("", "/")


@router.get("/admin/site-links", response_class=HTMLResponse)
def site_links_view(request: Request, db: DbSession, admin: CurrentAdmin) -> HTMLResponse:
    """The rendered block again — what «Отмена» swaps back in."""
    return render(request, "partials/site_links.html", _site_links(db), admin=admin)


@router.get("/admin/site-links/edit", response_class=HTMLResponse)
def site_links_edit(request: Request, db: DbSession, admin: CurrentAdmin) -> HTMLResponse:
    return render(
        request,
        "partials/site_links_form.html",
        _form_context(_link_values(db)),
        admin=admin,
    )


@router.post("/admin/site-links", response_class=HTMLResponse)
def site_links_save(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    github: str = Form(""),
    telegram: str = Form(""),
    vk: str = Form(""),
    youtube: str = Form(""),
    rights: str = Form(""),
) -> HTMLResponse:
    submitted = {"github": github, "telegram": telegram, "vk": vk, "youtube": youtube}

    cleaned: dict[str, str] = {}
    invalid: list[str] = []
    for slug in LINK_SLUGS:
        url = _clean_url(submitted[slug])
        if url is None:
            invalid.append(slug)
        else:
            cleaned[f"footer.{slug}"] = url

    if invalid:
        # Nothing is written: one bad URL leaves every stored value alone. The
        # form comes back with what the owner typed still in it (F37) and the
        # error beside the field that caused it.
        typed = {f"footer.{slug}": submitted[slug] for slug in LINK_SLUGS}
        typed[RIGHTS_KEY] = rights
        return render(
            request,
            "partials/site_links_form.html",
            _form_context(typed, invalid),
            admin=admin,
        )

    cleaned[RIGHTS_KEY] = rights.strip()
    for key, value in cleaned.items():
        _put_value(db, key, value)
    db.commit()

    context = _site_links(db)
    context["with_contacts"] = _editing_from_home(request)
    return render(
        request,
        "partials/site_links_saved.html",
        context,
        admin=admin,
        headers=toast_headers(translate("editable.saved")),
    )
