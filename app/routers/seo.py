"""robots.txt, sitemap.xml and the two icons browsers ask for at the root."""

from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse, Response
from sqlalchemy import select

from app.config import settings
from app.deps import DbSession
from app.models.album import Album
from app.models.post import Post, PostStatus
from app.models.project import Project

router = APIRouter(include_in_schema=False)

STATIC_PATHS = ["/", "/dev", "/photo", "/blog"]

ICONS = Path(__file__).resolve().parent.parent / "static" / "icons"

# A week. The mark is not going to change, and these are requested on paths we
# cannot append a version query to.
_ICON_CACHE = {"Cache-Control": "public, max-age=604800"}


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> PlainTextResponse:
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /login",
            "Disallow: /me",
            "Disallow: /search",
            "",
            f"Sitemap: {settings.site_url.rstrip('/')}/sitemap.xml",
            "",
        ]
    )
    return PlainTextResponse(body)


@router.get("/favicon.ico")
def favicon() -> FileResponse:
    """Asked for at the root, by browsers that never read the `<link>` tags."""
    return FileResponse(ICONS / "favicon.ico", media_type="image/x-icon", headers=_ICON_CACHE)


@router.get("/apple-touch-icon.png")
def apple_touch_icon() -> FileResponse:
    """Asked for at the root by iOS when a page is added to the home screen."""
    return FileResponse(ICONS / "apple-touch-icon.png", media_type="image/png", headers=_ICON_CACHE)


@router.get("/sitemap.xml")
def sitemap(db: DbSession) -> Response:
    base = settings.site_url.rstrip("/")
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    def add(path: str, lastmod: datetime | None = None) -> None:
        node = SubElement(urlset, "url")
        SubElement(node, "loc").text = f"{base}{path}"
        if lastmod is not None:
            SubElement(node, "lastmod").text = lastmod.date().isoformat()

    for path in STATIC_PATHS:
        add(path)

    # Only published content: the sitemap must never advertise a draft.
    for slug, updated in db.execute(
        select(Post.slug, Post.updated_at).where(Post.status == PostStatus.PUBLISHED)
    ):
        add(f"/blog/{slug}", updated)

    # `body_html` as well as published: a project with no long description has
    # no page of its own — `project_detail` answers 404 and its card links
    # straight to the repository — so listing one advertises a dead URL.
    for slug, updated in db.execute(
        select(Project.slug, Project.updated_at).where(
            Project.is_published.is_(True), Project.body_html != ""
        )
    ):
        add(f"/dev/{slug}", updated)

    for slug, updated in db.execute(
        select(Album.slug, Album.updated_at).where(Album.is_published.is_(True))
    ):
        add(f"/photo/{slug}", updated)

    # encoding="unicode" returns the markup without a declaration, so we add our own.
    body = '<?xml version="1.0" encoding="UTF-8"?>' + tostring(urlset, encoding="unicode")
    return Response(content=body.encode("utf-8"), media_type="application/xml")
