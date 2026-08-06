from typing import TYPE_CHECKING

from sqlalchemy import Computed, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.photo import Photo

# Weighted so a title match outranks a caption match. The two-argument form of
# to_tsvector is IMMUTABLE, which is what makes a generated column legal.
_ALBUM_SEARCH = (
    "setweight(to_tsvector('russian', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('russian', coalesce(caption, '')), 'B')"
)


class Album(Base, TimestampMixin):
    __tablename__ = "album"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False, default="")

    cover_photo_id: Mapped[int | None] = mapped_column(
        ForeignKey("photo.id", use_alter=True, name="fk_album_cover_photo", ondelete="SET NULL"),
        nullable=True,
    )

    is_published: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0, index=True)
    lang: Mapped[str] = mapped_column(String(5), nullable=False, default="ru")

    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed(_ALBUM_SEARCH, persisted=True)
    )

    photos: Mapped[list["Photo"]] = relationship(
        back_populates="album",
        cascade="all, delete-orphan",
        foreign_keys="Photo.album_id",
        order_by="Photo.sort_order",
    )
    cover_photo: Mapped["Photo | None"] = relationship(
        foreign_keys=[cover_photo_id], post_update=True
    )

    __table_args__ = (Index("ix_album_search", "search_vector", postgresql_using="gin"),)
