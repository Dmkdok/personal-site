import enum
from datetime import datetime

from sqlalchemy import Computed, DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin

_POST_SEARCH = (
    "setweight(to_tsvector('russian', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('russian', coalesce(excerpt, '')), 'B') || "
    "setweight(to_tsvector('russian', coalesce(body_md, '')), 'C')"
)


class PostStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Post(Base, TimestampMixin):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")

    body_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")

    cover_path: Mapped[str | None] = mapped_column(String(300))

    status: Mapped[PostStatus] = mapped_column(
        Enum(
            PostStatus,
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=PostStatus.DRAFT,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    lang: Mapped[str] = mapped_column(String(5), nullable=False, default="ru")

    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed(_POST_SEARCH, persisted=True)
    )

    __table_args__ = (Index("ix_post_search", "search_vector", postgresql_using="gin"),)
