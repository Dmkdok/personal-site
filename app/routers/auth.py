"""Login and logout. Not linked from public navigation."""

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.deps import DbSession, OptionalAdmin
from app.models.admin_user import AdminUser
from app.security import (
    client_ip,
    csrf_ok,
    csrf_token,
    end_session,
    hash_password,
    login_blocked,
    needs_rehash,
    record_login_attempt,
    start_session,
    verify_password,
)
from app.templating import render, translate

router = APIRouter(tags=["auth"])

# One message for every failure mode: an unknown username and a wrong password
# must be indistinguishable.
GENERIC_ERROR = translate("auth.invalid")
#: The window is configuration, so the message reads it rather than restating it.
THROTTLED_ERROR = translate("auth.throttled", minutes=settings.login_window_minutes)


def _safe_next(value: str | None) -> str:
    """Only allow same-site relative redirects."""
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


@router.get("/csrf")
def csrf(request: Request) -> JSONResponse:
    """The current session's CSRF token, for a client whose copy went stale.

    `ui.js` asks for one when a save comes back 403 and retries it once, rather
    than telling the owner to reload a page that still holds unsaved text (SPEC
    edge case 5). Not a secret being handed out: it is this session's own token,
    reachable only with this session's cookie, and the same-origin policy stops
    another site from reading the answer.
    """
    return JSONResponse({"token": csrf_token(request)})


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
        return fail(translate("auth.stale_form"), 403)

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
