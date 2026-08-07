"""Authentication, CSRF and login throttling.

There is exactly one account. Everything here is deliberately small: a signed
session cookie carrying a token that the database can invalidate, Argon2id
hashing, a header-based CSRF check enforced in middleware rather than per route,
and IP throttling backed by a table so it survives a restart.
"""

import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.admin_user import AdminUser, LoginAttempt

_hasher = PasswordHasher()

SESSION_USER_KEY = "uid"
SESSION_TOKEN_KEY = "stk"
SESSION_CSRF_KEY = "csrf"

CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Exempt from the *middleware* check only. Both are plain HTML forms that cannot
# set a header, so they carry the token in a hidden field and verify it inside
# the route — reading a body in middleware would consume it for the handler.
CSRF_EXEMPT_PATHS = frozenset({"/login", "/logout"})


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False
    return True


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return True


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


# --------------------------------------------------------------------------
# Session
# --------------------------------------------------------------------------
def start_session(request: Request, user: AdminUser) -> None:
    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id
    request.session[SESSION_TOKEN_KEY] = user.session_token
    request.session[SESSION_CSRF_KEY] = secrets.token_urlsafe(32)


def end_session(request: Request, db: Session, user: AdminUser | None) -> None:
    """Clear the cookie *and* rotate the stored token, so old cookies die too."""
    if user is not None:
        user.session_token = new_session_token()
        db.add(user)
        db.commit()
    request.session.clear()


def current_admin(request: Request, db: Session) -> AdminUser | None:
    user_id = request.session.get(SESSION_USER_KEY)
    token = request.session.get(SESSION_TOKEN_KEY)
    if not user_id or not token:
        return None

    user = db.get(AdminUser, user_id)
    if user is None or not secrets.compare_digest(user.session_token, token):
        request.session.clear()
        return None
    return user


# --------------------------------------------------------------------------
# CSRF
# --------------------------------------------------------------------------
def csrf_token(request: Request) -> str:
    """Return the session's CSRF token, creating one for anonymous visitors."""
    token = request.session.get(SESSION_CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[SESSION_CSRF_KEY] = token
    return token


def csrf_ok(request: Request, submitted: str | None) -> bool:
    expected = request.session.get(SESSION_CSRF_KEY)
    if not expected or not submitted:
        return False
    return secrets.compare_digest(expected, submitted)


# --------------------------------------------------------------------------
# Login throttling
# --------------------------------------------------------------------------
def client_ip(request: Request) -> str:
    """The peer the request actually came from.

    Deliberately does **not** read `X-Forwarded-For`. That header is written by
    the client, and taking its leftmost entry turned F17's budget into
    decoration: a rotating value bought a fresh five attempts every time, and
    the suite stayed green only because no test sent the header.

    Behind a proxy, uvicorn's `--proxy-headers` applies it for us — but only
    for peers named in `--forwarded-allow-ips`, which is the one place that
    knows which proxy is ours. One resolver that checks, rather than two where
    the second does not.
    """
    return (request.client.host if request.client else "unknown")[:45]


def login_blocked(db: Session, ip: str) -> bool:
    since = datetime.now(UTC) - timedelta(minutes=settings.login_window_minutes)
    failures = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.ip == ip,
            LoginAttempt.success.is_(False),
            LoginAttempt.attempted_at >= since,
        )
    )
    return bool(failures and failures >= settings.login_max_attempts)


def record_login_attempt(db: Session, ip: str, *, success: bool) -> None:
    db.add(LoginAttempt(ip=ip, success=success))
    if success:
        # A successful login clears the slate for that address.
        db.query(LoginAttempt).filter(
            LoginAttempt.ip == ip, LoginAttempt.success.is_(False)
        ).delete()
    db.commit()


# --------------------------------------------------------------------------
# Seeding
# --------------------------------------------------------------------------
def ensure_admin_user(db: Session) -> AdminUser:
    """Create the single admin from the environment, or update a changed password."""
    user = db.scalar(select(AdminUser).limit(1))
    if user is None:
        user = AdminUser(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            session_token=new_session_token(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    changed = False
    if user.username != settings.admin_username:
        user.username = settings.admin_username
        changed = True
    if not verify_password(user.password_hash, settings.admin_password):
        # The password in the environment is the source of truth: changing it
        # there and restarting is how the owner rotates it.
        user.password_hash = hash_password(settings.admin_password)
        user.session_token = new_session_token()
        changed = True
    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
