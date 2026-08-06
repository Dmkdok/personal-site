"""Site-wide search results."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app.deps import DbSession, OptionalAdmin
from app.services import search as search_service
from app.templating import render

router = APIRouter(tags=["search"])


@router.get("/search", response_class=HTMLResponse)
def search_page(
    request: Request,
    db: DbSession,
    admin: OptionalAdmin,
    q: str = Query("", max_length=200),
) -> HTMLResponse:
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
            "min_length": search_service.MIN_QUERY_LENGTH,
        },
        admin=admin,
    )
