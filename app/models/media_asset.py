from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MediaAsset(Base):
    """One stored upload, keyed by the SHA-256 of the bytes that produced it.

    This is the whole of the deduplication mechanism (F42): an upload whose
    digest is already here reuses the stored paths and writes nothing.

    It is deliberately *not* a reference table. Deletion asks the content tables
    who still points at a file rather than reading a count from here (ADR-013),
    because a count that drifts too low deletes a file that is still on a page —
    the exact failure that design exists to prevent.
    """

    __tablename__ = "media_asset"

    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)

    #: `<kind>/<group>/<uuid>` — the original's path without its extension, and
    #: the prefix every `<stem>_<width>.webp` rendition shares. Indexed because
    #: `images.release` looks a stem up on every deletion.
    stem: Mapped[str] = mapped_column(String(300), nullable=False, index=True)

    original_path: Mapped[str] = mapped_column(String(300), nullable=False)

    width: Mapped[int] = mapped_column(nullable=False, default=0)
    height: Mapped[int] = mapped_column(nullable=False, default=0)
    byte_size: Mapped[int] = mapped_column(nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
