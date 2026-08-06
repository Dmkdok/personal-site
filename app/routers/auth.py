"""Login and logout. Not linked from public navigation."""

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.deps import DbSession, OptionalAdmin
from app.models.admin_user import AdminUser
from app.security import (
    client_ip,
    csrf_ok,
    end_session,
    hash_password,
    login_blocked,
    needs_rehash,
    record_login_attempt,
    start_session,
    verify_password,
)
from app.templating import render

router = APIRouter(tags=["auth"])

# One message for every failure mode: an unknown username and a wrong password
# must be indistinguishable.
GENERIC_ERROR = "Неверный логин или пароль."
THROTTLED_ERROR = "Слишком много попыток входа. Попробуйте через 15 минут."


def _safe_next(value: str | None) -> str:
    """Only allow same-site relative redirects."""
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, admin: OptionalAdmin, next: str = "/") -> HTMLResponse:
    if admin is not None:
        return RedirectResponse(_safe_next(next), status_code=status.HTTP_303_SEE_OTHER)
    return render(request, "pages/login.html", {"next": _safe_next(next)})


@router.post("/login")
def login(
    request: Request,
    db: DbSession,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    next: str = Form("/"),
):
    destination = _safe_next(next)
    ip = client_ip(request)

    def fail(message: str, code: int) -> HTMLResponse:
        return render(
            request,
            "pages/login.html",
            {"error": message, "next": destination, "username": username},
            status_code=code,
        )

    if not csrf_ok(request, csrf_token):
        return fail("Форма устарела. Обновите страницу и попробуйте снова.", 403)

    if login_blocked(db, ip):
        return fail(THROTTLED_ERROR, status.HTTP_429_TOO_MANY_REQUESTS)

    user = db.scalar(select(AdminUser).where(AdminUser.username == username))
    if user is None or not verify_password(user.password_hash, password):
        record_login_attempt(db, ip, success=False)
        return fail(GENERIC_ERROR, status.HTTP_401_UNAUTHORIZED)

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.add(user)
        db.commit()

    record_login_attempt(db, ip, success=True)
    start_session(request, user)
    return RedirectResponse(destination, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(
    request: Request,
    db: DbSession,
    admin: OptionalAdmin,
    csrf_token: str = Form(""),
):
    # Plain form, so the CSRF token arrives as a field rather than a header.
    if not csrf_ok(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF")
    end_session(request, db, admin)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
