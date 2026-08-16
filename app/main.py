"""Application factory: middleware, routers, startup hooks."""

import logging
import secrets
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app import background
from app.config import settings
from app.db import SessionLocal, engine
from app.routers import auth, blog, me, pages, photos, projects, search, seo
from app.security import CSRF_EXEMPT_PATHS, CSRF_HEADER, SAFE_METHODS, csrf_ok, ensure_admin_user
from app.templating import templates, translate

LOG_FORMAT = "%(levelname)s [%(name)s] %(message)s"

# 5 MB per file, four files at most: the log the owner reads is the recent one,
# and 20 MB is small beside the photographs sharing the appliance while still
# holding weeks of an unattended site's INFO lines. The ceiling exists so that
# nothing on this host can grow without bound (F60); the container's own log is
# capped separately, by the `logging:` block in both deployment files.
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


def _configure_logging() -> None:
    """Console always; a file beside it when LOG_DIR is set.

    The file handler is *added* to the stream, never substituted for it, so
    `docker logs` keeps showing exactly what it showed before — same format,
    same lines.

    A log path is never the reason the site is down: a directory that cannot be
    created or written degrades to stdout with a warning instead of raising at
    startup, when the alternative would be a site that is down because a mount
    was missing.
    """
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    if not settings.log_dir:
        return

    directory = Path(settings.log_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            directory / "app.log",
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError as exc:
        logging.getLogger("portfolio").warning(
            "LOG_DIR %s is not usable (%s); logging to stdout only", directory, exc
        )
        return

    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(handler)


_configure_logging()
logger = logging.getLogger("portfolio")

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"


def _run_migrations() -> None:
    """Bring the database up to head. Idempotent, so safe on every boot."""
    from alembic import command
    from alembic.config import Config

    root = APP_DIR.parent
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    # Leave logging alone: env.py must not reconfigure the root logger here.
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    logger.info("database migrated to head")


def _ensure_media_dirs() -> None:
    for directory in (settings.originals_dir, settings.derived_dir):
        directory.mkdir(parents=True, exist_ok=True)


def _seed_admin() -> None:
    db = SessionLocal()
    try:
        user = ensure_admin_user(db)
        logger.info("admin account ready: %s", user.username)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_media_dirs()
    _run_migrations()
    _seed_admin()
    # Photos left mid-processing by a restart are picked up again here.
    background.run_recovery()
    yield
    background.shutdown()


async def _csrf_guard(request: Request, call_next):
    """Reject unsafe requests without a valid CSRF token.

    Enforced centrally rather than per route: a new endpoint is protected by
    default instead of by remembering to add a dependency.
    """
    if (
        request.method not in SAFE_METHODS
        and request.url.path not in CSRF_EXEMPT_PATHS
        and not csrf_ok(request, request.headers.get(CSRF_HEADER))
    ):
        return JSONResponse({"detail": translate("errors.csrf")}, status_code=403)
    return await call_next(request)


def apply_security_headers(response: Response, nonce: str) -> Response:
    """Stamp the policy onto one response.

    A function rather than middleware-only code because an unhandled exception
    never reaches the middleware on the way out: Starlette's
    `ServerErrorMiddleware` sits *outside* the user stack, so the 500 it builds
    used to leave with no CSP and no `X-Frame-Options` at all — the one response
    most likely to be carrying a stack trace's worth of detail.
    """
    response.headers["Content-Security-Policy"] = "; ".join(
        [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}'",
            "style-src 'self'",
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "object-src 'none'",
        ]
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


async def _security_headers(request: Request, call_next):
    # A per-request nonce lets the pre-paint theme script run under a policy
    # that otherwise forbids inline script.
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce

    response: Response = await call_next(request)
    return apply_security_headers(response, nonce)


def create_app() -> FastAPI:
    app = FastAPI(
        title="portfolio",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    # Added innermost-first: the outermost middleware is the last one added.
    # Order at runtime: security headers → session → CSRF → routes.
    app.middleware("http")(_csrf_guard)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="portfolio_session",
        max_age=settings.session_max_age_days * 24 * 60 * 60,
        same_site="lax",
        https_only=settings.is_production,
    )
    app.middleware("http")(_security_headers)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # Only the derived renditions are reachable over HTTP. Originals stay on the
    # volume as the source of truth and are never served (SPEC: no downloads).
    _ensure_media_dirs()
    app.mount("/media", StaticFiles(directory=settings.derived_dir), name="media")

    app.include_router(auth.router)
    app.include_router(pages.router)
    app.include_router(projects.router)
    app.include_router(photos.router)
    app.include_router(blog.router)
    app.include_router(search.router)
    app.include_router(me.router)
    app.include_router(seo.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # htmx swaps the response body in place, so an error must not replace a
        # fragment with a whole page.
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if exc.status_code == 404:
            return templates.TemplateResponse(request, "pages/404.html", status_code=404)
        if exc.status_code >= 500:
            return templates.TemplateResponse(
                request, "pages/500.html", status_code=exc.status_code
            )
        if exc.status_code == 401 and request.method == "GET":
            # Send the admin to the login form and back to where they were.
            return RedirectResponse(
                f"/login?next={quote(request.url.path, safe='/')}", status_code=303
            )
        return HTMLResponse(str(exc.detail), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled error on %s", request.url.path)
        nonce = getattr(request.state, "csp_nonce", "")
        if request.headers.get("HX-Request") == "true":
            response: Response = JSONResponse(
                {"detail": translate("errors.internal")}, status_code=500
            )
        else:
            response = templates.TemplateResponse(request, "pages/500.html", status_code=500)
        # This handler runs outside the middleware that would normally do it.
        return apply_security_headers(response, nonce)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
