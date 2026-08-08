"""Blog: Markdown articles with drafts and in-place editing.

Everything the owner does to an article happens on the article's own surface —
the index for creating, the article page for editing and deleting, the editor
for writing. There is no separate admin area.

The editor's preview and the published page both go through
`app.services.markdown.render_markdown`, so what the preview shows is exactly
what gets stored in `body_html`.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import select

from app.deps import CurrentAdmin, DbSession, OptionalAdmin
from app.models.post import Post, PostStatus
from app.services.images import (
    COVER,
    POSTS,
    PROSE,
    UNFILED,
    ImageRejected,
    cover_sources,
    group_name,
    media_url,
    release,
    stems_in_text,
    store_and_process,
)
from app.services.markdown import excerpt_from, render_markdown
from app.services.slugs import unique_slug
from app.templating import render, toast_headers, translate

router = APIRouter(prefix="/blog", tags=["blog"])

POST_KIND = POSTS


# --------------------------------------------------------------------------
# View helpers, passed into the templates rather than registered globally so
# this module cannot affect anyone else's pages.
# --------------------------------------------------------------------------
def ru_date(value: datetime | None) -> str:
    """«4 августа 2026» — written out, because a card has room for it."""
    if value is None:
        return ""
    return f"{value.day} {translate(f'blog.months.{value.month}')} {value.year}"


def iso_date(value: datetime | None) -> str:
    return value.date().isoformat() if value else ""


def _ctx(**values) -> dict:
    """Template context with the blog's view helpers already in it."""
    return {
        "active_section": "blog",
        "ru_date": ru_date,
        "iso_date": iso_date,
        "cover_sources": cover_sources,
        **values,
    }


def _get_post(db: DbSession, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=translate("blog.not_found")
        )
    return post


def _now_hm() -> str:
    return datetime.now(UTC).strftime("%H:%M")


# --------------------------------------------------------------------------
# Writing: the form fields shared by save, publish and unpublish.
# --------------------------------------------------------------------------
def _apply_form(
    db: DbSession,
    post: Post,
    *,
    title: str | None,
    slug: str | None,
    excerpt: str | None,
    body_md: str | None,
) -> None:
    """Fold submitted editor fields into the post. Every field is optional."""
    if title is not None:
        post.title = title.strip()[:250] or translate("blog.untitled")

    if slug is not None:
        wanted = slug.strip()
        if not wanted:
            # An emptied field means "rebuild the address from the title".
            post.slug = unique_slug(db, Post, post.title, exclude_id=post.id)
        elif wanted != post.slug:
            # Only a deliberate edit moves a published article's URL (F32).
            post.slug = unique_slug(db, Post, wanted, exclude_id=post.id)

    if body_md is not None:
        previous_auto = excerpt_from(post.body_md)
        previous_excerpt = post.excerpt
        post.body_md = body_md
        post.body_html = render_markdown(body_md)

        submitted = (excerpt or "").strip()
        looked_auto = previous_excerpt == previous_auto and submitted == previous_excerpt
        # Blank, or still holding the summary we generated last time: regenerate.
        post.excerpt = excerpt_from(body_md) if (not submitted or looked_auto) else submitted
    elif excerpt is not None:
        post.excerpt = excerpt.strip() or excerpt_from(post.body_md)


# --------------------------------------------------------------------------
# Public pages
# --------------------------------------------------------------------------
@router.get("", response_class=HTMLResponse)
def post_index(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    """Published articles, newest first. Drafts are listed for the owner only."""
    posts = list(
        db.scalars(
            select(Post)
            .where(Post.status == PostStatus.PUBLISHED)
            .order_by(Post.published_at.desc(), Post.id.desc())
        )
    )
    drafts: list[Post] = []
    if admin is not None:
        drafts = list(
            db.scalars(
                select(Post)
                .where(Post.status == PostStatus.DRAFT)
                .order_by(Post.updated_at.desc(), Post.id.desc())
            )
        )

    return render(
        request,
        "blog/index.html",
        _ctx(posts=posts, drafts=drafts),
        admin=admin,
    )


@router.get("/{slug}", response_class=HTMLResponse)
def post_detail(request: Request, db: DbSession, admin: OptionalAdmin, slug: str) -> HTMLResponse:
    post = db.scalar(select(Post).where(Post.slug == slug))
    # A draft simply does not exist for a visitor.
    if post is None or (post.status is not PostStatus.PUBLISHED and admin is None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=translate("blog.not_found")
        )

    return render(request, "blog/post.html", _ctx(post=post), admin=admin)


@router.get("/{slug}/edit", response_class=HTMLResponse)
def post_editor(request: Request, db: DbSession, admin: CurrentAdmin, slug: str) -> HTMLResponse:
    post = db.scalar(select(Post).where(Post.slug == slug))
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=translate("blog.not_found")
        )
    return render(
        request,
        "blog/editor.html",
        _ctx(post=post, saved_label=None, focus_action=False),
        admin=admin,
    )


# --------------------------------------------------------------------------
# Admin: creating, saving, publishing
# --------------------------------------------------------------------------
@router.get("/admin/new", response_class=HTMLResponse)
def new_post_form(request: Request, admin: CurrentAdmin) -> HTMLResponse:
    return render(request, "blog/_new_form.html", _ctx(), admin=admin)


@router.get("/admin/new/cancel", response_class=HTMLResponse)
def new_post_cancel(request: Request, admin: CurrentAdmin) -> HTMLResponse:
    return render(request, "blog/_new_button.html", _ctx(), admin=admin)


@router.post("/admin/posts")
def create_post(
    db: DbSession,
    admin: CurrentAdmin,
    title: str = Form(""),
) -> Response:
    """Create the draft and hand the owner straight to the editor."""
    clean_title = title.strip()[:250] or translate("blog.untitled")
    post = Post(
        slug=unique_slug(db, Post, clean_title),
        title=clean_title,
        excerpt="",
        body_md="",
        body_html="",
        status=PostStatus.DRAFT,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={
            "HX-Redirect": f"/blog/{post.slug}/edit",
            **toast_headers(translate("blog.toast_created")),
        },
    )


@router.post("/admin/preview", response_class=HTMLResponse)
def preview(admin: CurrentAdmin, body_md: str = Form("")) -> HTMLResponse:
    """The live preview.

    Deliberately the same call the published page is built from, so the two
    cannot drift apart.
    """
    return HTMLResponse(render_markdown(body_md))


@router.post("/admin/posts/{post_id}", response_class=HTMLResponse)
def save_post(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    post_id: int,
    title: str = Form(""),
    slug: str = Form(""),
    excerpt: str = Form(""),
    body_md: str = Form(""),
) -> HTMLResponse:
    post = _get_post(db, post_id)
    slug_before = post.slug
    pictures_before = stems_in_text(post.body_md, post.body_html)

    _apply_form(db, post, title=title, slug=slug, excerpt=excerpt, body_md=body_md)
    db.add(post)
    db.commit()
    db.refresh(post)

    # A picture cut out of the text stops being this article's (F41). Whether it
    # is anybody else's is `release`'s question, not ours: the same frame may be
    # this article's cover or another article's picture.
    release(db, *(pictures_before - stems_in_text(post.body_md, post.body_html)))

    headers: dict[str, str] = {}
    if post.slug != slug_before:
        # Keep the address bar honest so a reload lands on the same article.
        headers["HX-Replace-Url"] = f"/blog/{post.slug}/edit"

    return render(
        request,
        "blog/_save_state.html",
        _ctx(post=post, saved_label=translate("blog.saved_at", time=_now_hm())),
        admin=admin,
        headers=headers,
    )


@router.post("/admin/posts/{post_id}/publish", response_class=HTMLResponse)
def publish_post(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    post_id: int,
    title: str = Form(""),
    slug: str = Form(""),
    excerpt: str = Form(""),
    body_md: str = Form(""),
) -> HTMLResponse:
    """Publish what is on screen: the pending edits are saved in the same step."""
    post = _get_post(db, post_id)
    _apply_form(db, post, title=title, slug=slug, excerpt=excerpt, body_md=body_md)
    post.status = PostStatus.PUBLISHED
    if post.published_at is None:
        post.published_at = datetime.now(UTC)
    db.add(post)
    db.commit()
    db.refresh(post)

    return render(
        request,
        "blog/_editor_meta.html",
        _ctx(post=post, saved_label=translate("blog.saved_at", time=_now_hm()), focus_action=True),
        admin=admin,
        headers=toast_headers(translate("blog.toast_published")),
    )


@router.post("/admin/posts/{post_id}/unpublish", response_class=HTMLResponse)
def unpublish_post(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    post_id: int,
    title: str = Form(""),
    slug: str = Form(""),
    excerpt: str = Form(""),
    body_md: str = Form(""),
) -> HTMLResponse:
    post = _get_post(db, post_id)
    _apply_form(db, post, title=title, slug=slug, excerpt=excerpt, body_md=body_md)
    post.status = PostStatus.DRAFT
    # published_at is kept: republishing restores the original date rather than
    # pretending the article is new.
    db.add(post)
    db.commit()
    db.refresh(post)

    return render(
        request,
        "blog/_editor_meta.html",
        _ctx(post=post, saved_label=translate("blog.saved_at", time=_now_hm()), focus_action=True),
        admin=admin,
        headers=toast_headers(translate("blog.toast_unpublished")),
    )


@router.post("/admin/posts/{post_id}/delete")
def delete_post(db: DbSession, admin: CurrentAdmin, post_id: int) -> Response:
    post = _get_post(db, post_id)
    doomed = {post.cover_path, *stems_in_text(post.body_md, post.body_html)}
    db.delete(post)
    db.commit()
    # Only once the row is gone. `release` asks the database who still points at
    # each file, so a row still in flight would read as a live reference — and a
    # file another article shares is kept either way (F41, ADR-013).
    release(db, *doomed)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"HX-Redirect": "/blog", **toast_headers(translate("blog.toast_deleted"))},
    )


# --------------------------------------------------------------------------
# Admin: images
# --------------------------------------------------------------------------
@router.post("/admin/posts/{post_id}/cover", response_class=HTMLResponse)
def upload_cover(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    post_id: int,
    file: UploadFile | None = File(None),
) -> HTMLResponse:
    post = _get_post(db, post_id)
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail=translate("blog.image_no_file"))

    data = file.file.read()
    try:
        stored = store_and_process(
            db,
            data,
            file.filename,
            file.content_type,
            kind=POST_KIND,
            group=group_name(post.id, post.slug),
            profile=COVER,
        )
    except ImageRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    previous = post.cover_path
    post.cover_path = stored.derivatives[max(stored.derivatives)]
    db.add(post)
    db.commit()
    db.refresh(post)
    release(db, previous)

    return render(
        request,
        "blog/_editor_meta.html",
        _ctx(post=post, saved_label=None, focus_action=True),
        admin=admin,
        headers=toast_headers(translate("blog.toast_cover_saved")),
    )


@router.post("/admin/posts/{post_id}/cover/remove", response_class=HTMLResponse)
def remove_cover(
    request: Request, db: DbSession, admin: CurrentAdmin, post_id: int
) -> HTMLResponse:
    post = _get_post(db, post_id)
    previous = post.cover_path
    post.cover_path = None
    db.add(post)
    db.commit()
    db.refresh(post)
    release(db, previous)

    return render(
        request,
        "blog/_editor_meta.html",
        _ctx(post=post, saved_label=None, focus_action=True),
        admin=admin,
        headers=toast_headers(translate("blog.toast_cover_removed")),
    )


@router.post("/admin/images")
def upload_inline_image(
    db: DbSession,
    admin: CurrentAdmin,
    file: UploadFile | None = File(None),
    post_id: int | None = Form(None),
) -> JSONResponse:
    """Store a picture dropped into the editor and hand back Markdown for it.

    `post_id` says which article the picture belongs to, so it is filed with
    that article (F40). It is optional and unknown ids are ignored rather than
    refused: an editor that has not yet learnt to send it must keep working,
    and the picture then lands in `posts/_unfiled/`.
    """
    if file is None or not file.filename:
        return JSONResponse({"error": translate("blog.image_no_file")}, status_code=400)

    post = db.get(Post, post_id) if post_id else None
    group = group_name(post.id, post.slug) if post else UNFILED

    data = file.file.read()
    try:
        stored = store_and_process(
            db,
            data,
            file.filename,
            file.content_type,
            kind=POST_KIND,
            group=group,
            profile=PROSE,
        )
    except ImageRejected as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    # Nothing else in this request writes, so the asset row wants its own
    # commit: without it the next upload of the same frame stores it again.
    db.commit()

    url = media_url(stored.derivatives[max(stored.derivatives)])
    return JSONResponse({"url": url, "markdown": f"![{translate('blog.md.ph_alt')}]({url})"})
