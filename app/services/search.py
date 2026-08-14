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

#: Where each kind's hits live, so a hit's URL is built in one place.
URL_PREFIXES = {"post": "/blog/", "project": "/dev/", "album": "/photo/"}


@dataclass(slots=True)
class SearchHit:
    kind: str  # "post" | "project" | "album"
    title: str
    url: str
    note: str
    rank: float


@dataclass(slots=True)
class SearchGroup:
    """One content type's hits, and how many there really are.

    The list used to stop at twelve without saying so, which is a lie of
    omission on a search page: a visitor cannot tell «twelve matches» from
    «twelve of ninety» (UI-AUDIT F-014). The count comes from its own
    `count()` over the same predicate — the GIN index is already there.
    """

    kind: str  # "post" | "project" | "album"
    hits: list[SearchHit]
    total: int

    @property
    def shown(self) -> int:
        return len(self.hits)

    @property
    def has_more(self) -> bool:
        return self.shown < self.total

    def __bool__(self) -> bool:
        return bool(self.hits)

    def __iter__(self):
        return iter(self.hits)


@dataclass(slots=True)
class SearchResults:
    query: str
    posts: SearchGroup
    projects: SearchGroup
    albums: SearchGroup

    @property
    def groups(self) -> list[SearchGroup]:
        return [self.posts, self.projects, self.albums]

    @property
    def shown(self) -> int:
        """How many rows are on the page right now."""
        return sum(group.shown for group in self.groups)

    @property
    def total(self) -> int:
        """How many there are, which is the number worth stating."""
        return sum(group.total for group in self.groups)

    @property
    def is_empty(self) -> bool:
        return self.total == 0


def normalise(query: str | None) -> str:
    return " ".join((query or "").split())[:MAX_QUERY_LENGTH]


def is_searchable(query: str) -> bool:
    return len(query) >= MIN_QUERY_LENGTH


def _statement(kind: str, tsquery, include_hidden: bool):
    """The one query per content type, written once for the hits and the count."""
    if kind == "post":
        return select(
            Post.title,
            Post.slug,
            Post.excerpt,
            func.ts_rank(Post.search_vector, tsquery).label("rank"),
        ).where(
            Post.search_vector.op("@@")(tsquery),
            *([] if include_hidden else [Post.status == PostStatus.PUBLISHED]),
        )
    if kind == "project":
        return select(
            Project.title,
            Project.slug,
            Project.summary,
            func.ts_rank(Project.search_vector, tsquery).label("rank"),
        ).where(
            Project.search_vector.op("@@")(tsquery),
            *([] if include_hidden else [Project.is_published.is_(True)]),
        )
    if kind == "album":
        return select(
            Album.title,
            Album.slug,
            Album.caption,
            func.ts_rank(Album.search_vector, tsquery).label("rank"),
        ).where(
            Album.search_vector.op("@@")(tsquery),
            *([] if include_hidden else [Album.is_published.is_(True)]),
        )
    raise ValueError(f"unknown search kind: {kind}")


def group(
    db: Session,
    query: str,
    kind: str,
    *,
    limit: int = DEFAULT_LIMIT,
    include_hidden: bool = False,
) -> SearchGroup:
    """One content type's hits at `limit`, and the real total beside them."""
    query = normalise(query)
    if not is_searchable(query):
        return SearchGroup(kind=kind, hits=[], total=0)

    tsquery = func.websearch_to_tsquery("russian", query)
    statement = _statement(kind, tsquery, include_hidden)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(statement.order_by(desc("rank")).limit(limit)).all()
    prefix = URL_PREFIXES[kind]
    hits = [
        SearchHit(
            kind=kind,
            title=row[0],
            url=f"{prefix}{row[1]}",
            note=(row[2] or "").strip(),
            rank=float(row[3] or 0.0),
        )
        for row in rows
    ]
    return SearchGroup(kind=kind, hits=hits, total=total)


def search(db: Session, query: str, *, include_hidden: bool = False) -> SearchResults:
    """Run the query against all three content types.

    `include_hidden` is only ever true for a signed-in admin, so drafts and
    unpublished items never leak to visitors.
    """
    query = normalise(query)
    return SearchResults(
        query=query,
        posts=group(db, query, "post", include_hidden=include_hidden),
        projects=group(db, query, "project", include_hidden=include_hidden),
        albums=group(db, query, "album", include_hidden=include_hidden),
    )
