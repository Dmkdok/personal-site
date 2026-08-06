from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin


class AdminUser(Base, TimestampMixin):
    """The single account allowed to edit the site. There is never more than one."""

    __tablename__ = "admin_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Rotated on logout, which invalidates every cookie issued before it.
    session_token: Mapped[str] = mapped_column(String(64), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoginAttempt(Base):
    """One row per login attempt, used to throttle by IP."""

    __tablename__ = "login_attempt"

    id: Mapped[int] = mapped_column(primary_key=True)
    ip: Mapped[str] = mapped_column(String(45), index=True, nullable=False)
    success: Mapped[bool] = mapped_column(nullable=False, default=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
