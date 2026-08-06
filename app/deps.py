"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.admin_user import AdminUser
from app.security import current_admin

DbSession = Annotated[Session, Depends(get_db)]


def get_admin_optional(request: Request, db: DbSession) -> AdminUser | None:
    """The signed-in admin, or None. Public pages use this to reveal editing UI."""
    return current_admin(request, db)


OptionalAdmin = Annotated[AdminUser | None, Depends(get_admin_optional)]


def require_admin(admin: OptionalAdmin) -> AdminUser:
    """Guard for every mutating endpoint. Anonymous requests never get through."""
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется вход")
    return admin


CurrentAdmin = Annotated[AdminUser, Depends(require_admin)]
