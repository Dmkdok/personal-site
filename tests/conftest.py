"""Test fixtures.

Tests run against a real PostgreSQL database — the schema relies on generated
tsvector columns and the Russian text-search configuration, so an in-memory
substitute would not exercise what ships.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

TEST_DB = "portfolio_test"


def _admin_url() -> str:
    """Connection URL for the `postgres` maintenance database."""
    base = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://portfolio:portfolio@localhost:5432/portfolio"
    )
    return base.rsplit("/", 1)[0] + "/postgres"


def _test_url() -> str:
    base = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://portfolio:portfolio@localhost:5432/portfolio"
    )
    return base.rsplit("/", 1)[0] + f"/{TEST_DB}"


def pytest_configure(config: pytest.Config) -> None:
    """Point the app at a throwaway database before anything imports settings."""
    tmp_media = Path(config.rootpath) / "data" / "test-media"
    tmp_media.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("ENV", "local")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-to-pass-validation")
    os.environ.setdefault("ADMIN_USERNAME", "admin")
    os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
    os.environ["MEDIA_ROOT"] = str(tmp_media)

    engine = sa.create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)'))
        conn.execute(sa.text(f'CREATE DATABASE "{TEST_DB}"'))
    engine.dispose()

    os.environ["DATABASE_URL"] = _test_url()


@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    """Build the schema exactly the way production does — via the migrations.

    `Base.metadata.create_all` would skip the migration path entirely, and the
    generated tsvector columns are defined there.
    """
    from alembic import command
    from alembic.config import Config

    from app.config import settings
    from app.db import SessionLocal
    from app.security import ensure_admin_user

    root = Path(__file__).resolve().parent.parent
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")

    db = SessionLocal()
    try:
        ensure_admin_user(db)
    finally:
        db.close()


@pytest.fixture(scope="session")
def app_module(_schema):
    from app.main import create_app

    return create_app()


@pytest.fixture
def db(_schema) -> Iterator[Session]:
    from app.db import SessionLocal

    # `expire_on_commit=True` only here, not in the app. Tests assert on rows the
    # application changed through its own session, and the idiom for that is
    # `db.rollback()` before re-reading. With the app default (`False`) a fixture's
    # own `commit()` leaves its objects unexpired, and `rollback()` is a pass-through
    # when no transaction is open — so `db.get(...)` would hand back the stale
    # identity-mapped row and the assertion would test nothing.
    session = SessionLocal(expire_on_commit=True)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(app_module) -> Iterator["TestClient"]:  # noqa: F821
    from starlette.testclient import TestClient

    with TestClient(app_module) as test_client:
        yield test_client


@pytest.fixture
def admin_client(app_module) -> Iterator["TestClient"]:  # noqa: F821
    """An independent client with an authenticated admin session and a CSRF token.

    Deliberately its own `TestClient` rather than the `client` fixture logged in.
    Sharing one cookie jar made `client` an admin too, which quietly turned every
    "a visitor must not see this" assertion in a test that takes both fixtures
    into a test of the admin view.
    """
    from starlette.testclient import TestClient

    with TestClient(app_module) as test_client:
        page = test_client.get("/login")
        csrf = page.text.split('name="csrf_token" value="')[1].split('"')[0]
        response = test_client.post(
            "/login",
            data={
                "username": os.environ["ADMIN_USERNAME"],
                "password": os.environ["ADMIN_PASSWORD"],
                "csrf_token": csrf,
                "next": "/",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text
        test_client.headers["X-CSRF-Token"] = _csrf_from_page(test_client.get("/").text)
        yield test_client


def _csrf_from_page(html: str) -> str:
    return html.split('X-CSRF-Token": "')[1].split('"')[0]


@pytest.fixture
def csrf_from_page():
    return _csrf_from_page
