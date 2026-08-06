"""Application factory: middleware, routers, startup hooks."""

import logging
import secrets
from contextlib import asynccontextmanager
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
from app.routers import auth, blog, pages, photos, projects, search, seo
from app.security import CSRF_EXEMPT_PATHS, CSRF_HEADER, SAFE_METHODS, csrf_ok, ensure_admin_user
from app.templating import templates

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
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
    if request.method not in SAFE_METHODS and request.url.path not in CSRF_EXEMPT_PATHS:
        if not csrf_ok(request, request.headers.get(CSRF_HEADER)):
            return JSONResponse({"detail": "Недействительный CSRF-токен"}, status_code=403)
    return await call_next(request)


async def _security_headers(request: Request, call_next):
    # A per-request nonce lets the pre-paint theme script run under a policy
    # that otherwise forbids inline script.
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce

    response: Response = await call_next(request)

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
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"detail": "Внутренняя ошибка"}, status_code=500)
        return templates.TemplateResponse(request, "pages/500.html", status_code=500)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
