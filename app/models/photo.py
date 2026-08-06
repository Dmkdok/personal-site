import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.album import Album


class PhotoStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Photo(Base):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    album_id: Mapped[int] = mapped_column(
        ForeignKey("album.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Paths are relative to MEDIA_ROOT so the volume can be relocated.
    original_path: Mapped[str] = mapped_column(String(300), nullable=False)
    thumb_path: Mapped[str | None] = mapped_column(String(300))
    medium_path: Mapped[str | None] = mapped_column(String(300))
    large_path: Mapped[str | None] = mapped_column(String(300))

    width: Mapped[int | None] = mapped_column()
    height: Mapped[int | None] = mapped_column()
    byte_size: Mapped[int | None] = mapped_column()

    alt: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0, index=True)

    status: Mapped[PhotoStatus] = mapped_column(
        Enum(PhotoStatus, native_enum=False, length=16, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=PhotoStatus.PENDING,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    album: Mapped["Album"] = relationship(back_populates="photos", foreign_keys=[album_id])
