"""Development: a hand-curated shortlist of projects, edited in place on /dev.

Everything the owner does — add, edit, reorder, publish, delete — happens on the
public page through htmx swaps of the partials in `templates/dev/`. There is no
GitHub sync: the cards are typed by hand and ordered by hand.
"""

import re
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select

from app.deps import CurrentAdmin, DbSession, OptionalAdmin
from app.models.project import Project
from app.services import images
from app.services.markdown import excerpt_from, render_markdown
from app.services.slugs import unique_slug
from app.templating import render, toast_headers, translate

router = APIRouter(prefix="/dev", tags=["dev"])

COVER_KIND = images.PROJECTS

MAX_TITLE = 250
MAX_SUMMARY = 400
MAX_URL = 500
MAX_STACK_ITEMS = 12
MAX_STACK_ITEM_LENGTH = 40

# Only these two schemes ever reach the page; anything else is a phishing or
# javascript: vector, so it is refused with a message instead of being stored.
ALLOWED_URL_SCHEMES = ("http://", "https://")

_STACK_SEPARATORS = re.compile(r"[,\n;]")


class ProjectInvalid(Exception):
    """Input the owner can fix. Reported inline, never as a traceback."""


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
def _visible(db: DbSession, admin: Any) -> list[Project]:
    """Projects in the owner's order. Visitors never see unpublished ones."""
    query = select(Project).order_by(Project.sort_order, Project.id)
    if admin is None:
        query = query.where(Project.is_published.is_(True))
    return list(db.scalars(query))


def _get(db: DbSession, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=translate("dev.not_found"))
    return project


def _context(db: DbSession, admin: Any, form: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "active_section": "dev",
        "projects": _visible(db, admin),
        "form": form,
        "media_url": images.media_url,
        "cover_sources": images.cover_sources,
    }


def _board(
    request: Request,
    db: DbSession,
    admin: Any,
    *,
    form: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> HTMLResponse:
    """The whole editable surface: the open form, if any, plus the ordered list.

    Every mutation returns this, so ordering and the first/last markers on the
    move buttons can never drift out of step with the database.
    """
    return render(
        request, "dev/_board.html", _context(db, admin, form), admin=admin, headers=headers
    )


def _retarget_board() -> dict[str, str]:
    """Send a form's successful response to the board instead of the form.

    The form targets itself so that a validation error can come back in place
    with the typed text intact; a save has to replace the whole board.
    """
    return {"HX-Retarget": "#project-board", "HX-Reswap": "outerHTML"}


# --------------------------------------------------------------------------
# Input handling
# --------------------------------------------------------------------------
def _clean_url(raw: str, label_key: str) -> str | None:
    value = (raw or "").strip()
    if not value:
        return None
    field = translate(label_key)
    if len(value) > MAX_URL:
        raise ProjectInvalid(translate("dev.error_url_long", field=field, limit=MAX_URL))
    lowered = value.lower()
    if not lowered.startswith(ALLOWED_URL_SCHEMES) or len(lowered.split("//", 1)[1].strip()) == 0:
        raise ProjectInvalid(translate("dev.error_url", field=field))
    return value


def _clean_stack(raw: str) -> list[str]:
    """A comma- or newline-separated list, order preserved, duplicates dropped."""
    result: list[str] = []
    seen: set[str] = set()
    for part in _STACK_SEPARATORS.split(raw or ""):
        item = " ".join(part.split())[:MAX_STACK_ITEM_LENGTH]
        if not item or item.casefold() in seen:
            continue
        seen.add(item.casefold())
        result.append(item)
    if len(result) > MAX_STACK_ITEMS:
        raise ProjectInvalid(translate("dev.error_stack_many", limit=MAX_STACK_ITEMS))
    return result


def _parse(values: dict[str, str]) -> dict[str, Any]:
    title = " ".join((values.get("title") or "").split())
    if not title:
        raise ProjectInvalid(translate("dev.error_title_required"))
    if len(title) > MAX_TITLE:
        raise ProjectInvalid(translate("dev.error_title_long", limit=MAX_TITLE))

    summary = (values.get("summary") or "").strip()
    if len(summary) > MAX_SUMMARY:
        raise ProjectInvalid(translate("dev.error_summary_long", limit=MAX_SUMMARY))

    return {
        "title": title,
        "summary": summary,
        "body_md": (values.get("body_md") or "").strip(),
        "repo_url": _clean_url(values.get("repo_url", ""), "dev.field_repo"),
        "demo_url": _clean_url(values.get("demo_url", ""), "dev.field_demo"),
        "tech_stack": _clean_stack(values.get("tech_stack", "")),
    }


def _store_cover(db: DbSession, cover: UploadFile | None, group: str) -> str | None:
    """Validate and render one cover. Returns the stored derivative's path.

    `group` is the project's own directory, so a project's cover sits with the
    project it belongs to rather than among every cover uploaded that year.
    """
    if cover is None or not cover.filename:
        return None
    data = cover.file.read()
    if not data:
        return None
    try:
        stored = images.store_and_process(
            db,
            data,
            cover.filename,
            cover.content_type,
            kind=COVER_KIND,
            group=group,
            profile=images.COVER,
        )
    except images.ImageRejected as exc:
        raise ProjectInvalid(str(exc)) from exc
    # The widest rendition. The card asks for a narrower one through `srcset`.
    return stored.derivatives[max(stored.derivatives)]


# --------------------------------------------------------------------------
# Form state passed to the template
# --------------------------------------------------------------------------
def _blank_values() -> dict[str, Any]:
    return {
        "title": "",
        "summary": "",
        "body_md": "",
        "repo_url": "",
        "demo_url": "",
        "tech_stack": "",
        "cover_path": None,
    }


def _values_of(project: Project) -> dict[str, Any]:
    return {
        "title": project.title,
        "summary": project.summary,
        "body_md": project.body_md,
        "repo_url": project.repo_url or "",
        "demo_url": project.demo_url or "",
        "tech_stack": ", ".join(project.tech_stack or []),
        "cover_path": project.cover_path,
    }


def _new_form(values: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
    return {
        "dom_id": "project-form",
        "action": "/dev/admin/projects",
        "heading": translate("dev.form_new_title"),
        "submit": translate("dev.create"),
        "values": values or _blank_values(),
        "error": error,
    }


def _edit_form(
    project: Project, values: dict[str, Any] | None = None, error: str | None = None
) -> dict[str, Any]:
    return {
        "dom_id": f"project-{project.id}",
        "action": f"/dev/admin/projects/{project.id}",
        "heading": translate("dev.form_edit_title"),
        "submit": translate("dev.save"),
        "values": values or _values_of(project),
        "error": error,
    }


def _form_response(request: Request, admin: Any, form: dict[str, Any]) -> HTMLResponse:
    """Re-render a form with its error, keeping everything that was typed.

    Deliberately a 200: htmx does not swap error responses, and swapping the
    form back in is exactly how the typed content survives a rejected save.
    """
    return render(
        request,
        "dev/_project_form.html",
        {"form": form, "media_url": images.media_url},
        admin=admin,
        headers=toast_headers(form["error"], "error"),
    )


def _submitted(
    title: str,
    summary: str,
    body_md: str,
    repo_url: str,
    demo_url: str,
    tech_stack: str,
    cover_path: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "summary": summary,
        "body_md": body_md,
        "repo_url": repo_url,
        "demo_url": demo_url,
        "tech_stack": tech_stack,
        "cover_path": cover_path,
    }


# --------------------------------------------------------------------------
# Public pages
# --------------------------------------------------------------------------
@router.get("", response_class=HTMLResponse)
def project_index(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    return render(request, "dev/index.html", _context(db, admin), admin=admin)


# --------------------------------------------------------------------------
# Admin: in-place editing
# --------------------------------------------------------------------------
@router.get("/admin/board", response_class=HTMLResponse)
def project_board(request: Request, db: DbSession, admin: CurrentAdmin) -> HTMLResponse:
    """The board with no form open — what «Отмена» returns to."""
    return _board(request, db, admin)


@router.get("/admin/new", response_class=HTMLResponse)
def project_new(request: Request, db: DbSession, admin: CurrentAdmin) -> HTMLResponse:
    return _board(request, db, admin, form=_new_form())


@router.get("/admin/projects/{project_id}/edit", response_class=HTMLResponse)
def project_edit(
    request: Request, db: DbSession, admin: CurrentAdmin, project_id: int
) -> HTMLResponse:
    project = _get(db, project_id)
    return render(
        request,
        "dev/_project_form.html",
        {"form": _edit_form(project), "media_url": images.media_url},
        admin=admin,
    )


@router.post("/admin/projects", response_class=HTMLResponse)
def project_create(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    title: str = Form(""),
    summary: str = Form(""),
    body_md: str = Form(""),
    repo_url: str = Form(""),
    demo_url: str = Form(""),
    tech_stack: str = Form(""),
    cover: UploadFile | None = File(None),
) -> HTMLResponse:
    submitted = _submitted(title, summary, body_md, repo_url, demo_url, tech_stack)
    try:
        fields = _parse(submitted)
    except ProjectInvalid as exc:
        return _form_response(request, admin, _new_form(submitted, str(exc)))

    last = db.scalar(select(func.max(Project.sort_order)))
    project = Project(
        slug=unique_slug(db, Project, fields["title"]),
        body_html=render_markdown(fields["body_md"]),
        is_published=False,
        sort_order=(last or 0) + 1,
        **fields,
    )
    db.add(project)
    # Flushed before the cover is stored, because the cover's directory is named
    # after the project and the id only exists once the row does.
    db.flush()

    try:
        project.cover_path = _store_cover(db, cover, images.group_name(project.id, project.slug))
    except ProjectInvalid as exc:
        db.rollback()
        return _form_response(request, admin, _new_form(submitted, str(exc)))

    db.commit()

    return _board(
        request,
        db,
        admin,
        headers=toast_headers(translate("dev.toast_created")) | _retarget_board(),
    )


@router.post("/admin/projects/{project_id}", response_class=HTMLResponse)
def project_update(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    project_id: int,
    title: str = Form(""),
    summary: str = Form(""),
    body_md: str = Form(""),
    repo_url: str = Form(""),
    demo_url: str = Form(""),
    tech_stack: str = Form(""),
    remove_cover: str = Form(""),
    cover: UploadFile | None = File(None),
) -> HTMLResponse:
    project = _get(db, project_id)
    submitted = _submitted(
        title, summary, body_md, repo_url, demo_url, tech_stack, project.cover_path
    )
    try:
        fields = _parse(submitted)
        new_cover = _store_cover(db, cover, images.group_name(project.id, project.slug))
    except ProjectInvalid as exc:
        return _form_response(request, admin, _edit_form(project, submitted, str(exc)))

    previous_cover = project.cover_path
    pictures_before = images.stems_in_text(project.body_md, project.body_html)
    for name, value in fields.items():
        setattr(project, name, value)
    project.body_html = render_markdown(fields["body_md"])

    doomed: list[str | None] = []
    if new_cover:
        project.cover_path = new_cover
        doomed.append(previous_cover)
    elif remove_cover:
        project.cover_path = None
        doomed.append(previous_cover)

    # A published URL stays put; a draft's slug still follows its title.
    if not project.is_published:
        project.slug = unique_slug(db, Project, fields["title"], exclude_id=project.id)

    db.add(project)
    db.commit()

    # Only once the row is committed: `release` reads the database to find out
    # whether anything still points at each file (F41, ADR-013).
    doomed += pictures_before - images.stems_in_text(project.body_md, project.body_html)
    images.release(db, *doomed)

    return _board(
        request,
        db,
        admin,
        headers=toast_headers(translate("dev.toast_saved")) | _retarget_board(),
    )


@router.post("/admin/projects/{project_id}/publish", response_class=HTMLResponse)
def project_publish(
    request: Request, db: DbSession, admin: CurrentAdmin, project_id: int
) -> HTMLResponse:
    project = _get(db, project_id)
    project.is_published = not project.is_published
    db.add(project)
    db.commit()

    message = "dev.toast_published" if project.is_published else "dev.toast_unpublished"
    return _board(request, db, admin, headers=toast_headers(translate(message)))


@router.post("/admin/projects/{project_id}/move", response_class=HTMLResponse)
def project_move(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    project_id: int,
    direction: str = Form(""),
) -> HTMLResponse:
    """Keyboard-accessible reordering: the alternative to dragging."""
    project = _get(db, project_id)
    ordered = list(db.scalars(select(Project).order_by(Project.sort_order, Project.id)))
    index = ordered.index(project)
    target = index - 1 if direction == "up" else index + 1

    if direction in ("up", "down") and 0 <= target < len(ordered):
        ordered[index], ordered[target] = ordered[target], ordered[index]
        _renumber(db, ordered)
        return _board(request, db, admin, headers=toast_headers(translate("dev.toast_order")))

    # Already at the end of the list: nothing to do, and nothing to apologise for.
    return _board(request, db, admin)


@router.post("/admin/order", response_class=HTMLResponse)
def project_reorder(
    request: Request,
    db: DbSession,
    admin: CurrentAdmin,
    order: str = Form(""),
) -> HTMLResponse:
    """Apply the order produced by dragging: a comma-separated list of ids."""
    wanted = [int(part) for part in order.split(",") if part.strip().isdigit()]
    remaining = {
        project.id: project
        for project in db.scalars(select(Project).order_by(Project.sort_order, Project.id))
    }

    ordered: list[Project] = []
    for project_id in wanted:
        project = remaining.pop(project_id, None)
        if project is not None:
            ordered.append(project)
    # Anything the client did not mention keeps its relative place at the end.
    ordered.extend(remaining.values())

    _renumber(db, ordered)
    return _board(request, db, admin, headers=toast_headers(translate("dev.toast_order")))


@router.delete("/admin/projects/{project_id}", response_class=HTMLResponse)
def project_delete(
    request: Request, db: DbSession, admin: CurrentAdmin, project_id: int
) -> HTMLResponse:
    project = _get(db, project_id)
    doomed = {project.cover_path, *images.stems_in_text(project.body_md, project.body_html)}
    db.delete(project)
    db.commit()
    # Only once the row is gone, so a failed commit cannot orphan the page — and
    # a file another page shares survives, because `release` asks before it acts.
    images.release(db, *doomed)

    return _board(request, db, admin, headers=toast_headers(translate("dev.toast_deleted")))


def _renumber(db: DbSession, ordered: list[Project]) -> None:
    for position, project in enumerate(ordered):
        if project.sort_order != position:
            project.sort_order = position
            db.add(project)
    db.commit()


# --------------------------------------------------------------------------
# Detail page — registered last so /dev/admin/… can never be read as a slug
# --------------------------------------------------------------------------
@router.get("/{slug}", response_class=HTMLResponse)
def project_detail(
    request: Request, db: DbSession, admin: OptionalAdmin, slug: str
) -> HTMLResponse:
    project = db.scalar(select(Project).where(Project.slug == slug))

    # A project with no long description has no page of its own: its card links
    # straight to the repository instead of leading somewhere empty.
    if project is None or not project.body_html or (admin is None and not project.is_published):
        raise HTTPException(status_code=404, detail=translate("dev.not_found"))

    return render(
        request,
        "dev/detail.html",
        {
            "active_section": "dev",
            "project": project,
            "media_url": images.media_url,
            "cover_sources": images.cover_sources,
            "intrinsic_size": images.intrinsic_size,
            "meta_description": project.summary or excerpt_from(project.body_md, 160),
        },
        admin=admin,
    )
