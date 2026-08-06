"""robots.txt and sitemap.xml."""

from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select

from app.config import settings
from app.deps import DbSession
from app.models.album import Album
from app.models.post import Post, PostStatus
from app.models.project import Project

router = APIRouter(include_in_schema=False)

STATIC_PATHS = ["/", "/dev", "/photo", "/blog"]


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> PlainTextResponse:
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /login",
            "Disallow: /search",
            "",
            f"Sitemap: {settings.site_url.rstrip('/')}/sitemap.xml",
            "",
        ]
    )
    return PlainTextResponse(body)


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

    for slug, updated in db.execute(
        select(Project.slug, Project.updated_at).where(Project.is_published.is_(True))
    ):
        add(f"/dev/{slug}", updated)

    for slug, updated in db.execute(
        select(Album.slug, Album.updated_at).where(Album.is_published.is_(True))
    ):
        add(f"/photo/{slug}", updated)

    # encoding="unicode" returns the markup without a declaration, so we add our own.
    body = '<?xml version="1.0" encoding="UTF-8"?>' + tostring(urlset, encoding="unicode")
    return Response(content=body.encode("utf-8"), media_type="application/xml")
