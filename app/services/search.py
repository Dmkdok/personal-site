"""Site-wide search over articles, projects and albums.

Backed by the generated `search_vector` columns and PostgreSQL's Russian text
configuration — no external search engine (ADR-002).
"""

from dataclasses import dataclass

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.album import Album
from app.models.post import Post, PostStatus
from app.models.project import Project

MIN_QUERY_LENGTH = 2

#: Longer than any real search and short enough that the index never sees an
#: essay. Enforced by truncating rather than by refusing: a query that arrives
#: over the limit used to hit FastAPI's validator and answer a JSON 422 to a
#: browser asking for an HTML page.
MAX_QUERY_LENGTH = 200

DEFAULT_LIMIT = 12


@dataclass(slots=True)
class SearchHit:
    kind: str  # "post" | "project" | "album"
    title: str
    url: str
    note: str
    rank: float


@dataclass(slots=True)
class SearchResults:
    query: str
    posts: list[SearchHit]
    projects: list[SearchHit]
    albums: list[SearchHit]

    @property
    def total(self) -> int:
        return len(self.posts) + len(self.projects) + len(self.albums)

    @property
    def is_empty(self) -> bool:
        return self.total == 0


def normalise(query: str | None) -> str:
    return " ".join((query or "").split())[:MAX_QUERY_LENGTH]


def is_searchable(query: str) -> bool:
    return len(query) >= MIN_QUERY_LENGTH


def search(db: Session, query: str, *, include_hidden: bool = False) -> SearchResults:
    """Run the query against all three content types.

    `include_hidden` is only ever true for a signed-in admin, so drafts and
    unpublished items never leak to visitors.
    """
    query = normalise(query)
    if not is_searchable(query):
        return SearchResults(query=query, posts=[], projects=[], albums=[])

    tsquery = func.websearch_to_tsquery("russian", query)

    posts = _run(
        db,
        select(
            Post.title,
            Post.slug,
            Post.excerpt,
            func.ts_rank(Post.search_vector, tsquery).label("rank"),
        ).where(
            Post.search_vector.op("@@")(tsquery),
            *([] if include_hidden else [Post.status == PostStatus.PUBLISHED]),
        ),
        kind="post",
        url_prefix="/blog/",
    )

    projects = _run(
        db,
        select(
            Project.title,
            Project.slug,
            Project.summary,
            func.ts_rank(Project.search_vector, tsquery).label("rank"),
        ).where(
            Project.search_vector.op("@@")(tsquery),
            *([] if include_hidden else [Project.is_published.is_(True)]),
        ),
        kind="project",
        url_prefix="/dev/",
    )

    albums = _run(
        db,
        select(
            Album.title,
            Album.slug,
            Album.caption,
            func.ts_rank(Album.search_vector, tsquery).label("rank"),
        ).where(
            Album.search_vector.op("@@")(tsquery),
            *([] if include_hidden else [Album.is_published.is_(True)]),
        ),
        kind="album",
        url_prefix="/photo/",
    )

    return SearchResults(query=query, posts=posts, projects=projects, albums=albums)


def _run(db: Session, statement, *, kind: str, url_prefix: str) -> list[SearchHit]:
    rows = db.execute(statement.order_by(desc("rank")).limit(DEFAULT_LIMIT)).all()
    return [
        SearchHit(
            kind=kind,
            title=row[0],
            url=f"{url_prefix}{row[1]}",
            note=(row[2] or "").strip(),
            rank=float(row[3] or 0.0),
        )
        for row in rows
    ]
