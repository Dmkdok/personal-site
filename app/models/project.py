from sqlalchemy import Computed, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin

_PROJECT_SEARCH = (
    "setweight(to_tsvector('russian', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('russian', coalesce(summary, '')), 'B') || "
    "setweight(to_tsvector('russian', coalesce(body_md, '')), 'C')"
)


class Project(Base, TimestampMixin):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    body_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")

    repo_url: Mapped[str | None] = mapped_column(String(500))
    demo_url: Mapped[str | None] = mapped_column(String(500))
    tech_stack: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    cover_path: Mapped[str | None] = mapped_column(String(300))

    is_published: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0, index=True)
    lang: Mapped[str] = mapped_column(String(5), nullable=False, default="ru")

    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed(_PROJECT_SEARCH, persisted=True)
    )

    __table_args__ = (Index("ix_project_search", "search_vector", postgresql_using="gin"),)
