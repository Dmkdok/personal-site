"""Site-wide search results."""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.deps import DbSession, OptionalAdmin
from app.services import search as search_service
from app.templating import render, translate

router = APIRouter(tags=["search"])

#: The heading each group renders. Kept beside the route that serves one group
#: on its own, so a continuation cannot come back under a different name.
GROUP_LABELS = {
    "post": "search.group_posts",
    "project": "search.group_projects",
    "album": "search.group_albums",
}

#: A ceiling on the continuation. Without it `?limit=10000000` is a request to
#: rank every row in the table, from anyone.
MAX_GROUP_LIMIT = 200


@router.get("/search", response_class=HTMLResponse)
def search_page(
    request: Request,
    db: DbSession,
    admin: OptionalAdmin,
    q: str = Query(""),
) -> HTMLResponse:
    """Search results.

    No `max_length` on the parameter on purpose. It made an over-long query a
    validation failure, and FastAPI answers those with a JSON 422 — to a
    browser that asked for a page and gets a wall of `{"detail": …}`. The query
    is truncated instead and the page says so.
    """
    query = search_service.normalise(q)
    results = (
        search_service.search(db, query, include_hidden=admin is not None)
        if search_service.is_searchable(query)
        else None
    )

    return render(
        request,
        "pages/search.html",
        {
            "active_section": None,
            "query": query,
            "results": results,
            # The page renders the groups; nothing was swapped, so no group may
            # claim the caret. See `partials/search_group.html`.
            "swapped": False,
            "min_length": search_service.MIN_QUERY_LENGTH,
            "max_length": search_service.MAX_QUERY_LENGTH,
            "was_truncated": len(" ".join(q.split())) > search_service.MAX_QUERY_LENGTH,
        },
        admin=admin,
    )


@router.get("/search/group", response_class=HTMLResponse)
def search_group(
    request: Request,
    db: DbSession,
    admin: OptionalAdmin,
    q: str = Query(""),
    kind: str = Query(""),
    limit: int = Query(search_service.DEFAULT_LIMIT),
) -> HTMLResponse:
    """One group, longer — what «Показать ещё» asks for (UI-AUDIT F-014).

    It returns the whole group rather than the next slice, and the page swaps
    the section for it: the count in the heading, the list and the button are
    then rendered together from one query, and cannot disagree about how much
    is left. The alternative — appending rows on the client — leaves the button
    holding an offset the server never confirmed.
    """
    if kind not in GROUP_LABELS:
        raise HTTPException(status_code=404, detail=translate("errors.404_title"))

    query = search_service.normalise(q)
    bounded = max(search_service.DEFAULT_LIMIT, min(limit, MAX_GROUP_LIMIT))
    group = search_service.group(db, query, kind, limit=bounded, include_hidden=admin is not None)
    return render(
        request,
        "partials/search_group.html",
        {
            "group": group,
            "label": translate(GROUP_LABELS[kind]),
            "query": query,
            "swapped": True,
        },
        admin=admin,
    )
