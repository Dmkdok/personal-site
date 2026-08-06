from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SiteContent(Base):
    """Editable copy blocks (home intro, contact line, …), keyed by name and language."""

    __tablename__ = "site_content"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    lang: Mapped[str] = mapped_column(String(5), primary_key=True, default="ru")
    value_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    value_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
