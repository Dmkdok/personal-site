"""Fixtures for the Playwright suite.

These run from the host against the container `make up` started. The
"never run pytest on the host" rule in docs/CONVENTIONS.md is about Starlette's
TestClient, which deadlocks on Windows; Playwright talks HTTP to a real browser
and is unaffected.

The suite writes real content into the development database. Every fixture that
creates something registers it for deletion, so a repeated run starts from the
same place it did the first time.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, expect

from e2e.helpers import AdminApi, Album, Post, photo_bytes, ru, token

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "http://localhost:8000"


# ------------------------------------------------------------------ environment
def _load_dotenv(path: Path) -> None:
    """Parse `.env` into the process environment. pytest does not do this."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "launch_flow: one of the six flows on the launch checklist")
    config.addinivalue_line("markers", "a11y: accessibility evidence for T071")
    config.addinivalue_line(
        "markers", "perf: performance evidence for T072 (slow: builds 50 photos)"
    )


@pytest.fixture(scope="session")
def base_url(pytestconfig: pytest.Config) -> str:
    return (
        pytestconfig.getoption("--base-url") or os.environ.get("E2E_BASE_URL") or DEFAULT_BASE_URL
    )


@pytest.fixture(scope="session", autouse=True)
def _site_is_up(base_url: str) -> None:
    try:
        with urllib.request.urlopen(f"{base_url}/healthz", timeout=10) as response:
            assert response.status == 200
    except (urllib.error.URLError, OSError, AssertionError) as exc:  # pragma: no cover
        pytest.fail(f"{base_url}/healthz is not answering ({exc}). Start the stack with `make up`.")


@pytest.fixture(scope="session")
def admin_credentials() -> tuple[str, str]:
    """Read from the environment only — never a literal, never logged."""
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    if not username or not password:
        pytest.fail("ADMIN_USERNAME / ADMIN_PASSWORD are not set (expected in .env at the root).")
    return username, password


# ------------------------------------------------------------------------ auth
@pytest.fixture
def admin_storage_state(
    browser: Browser,
    base_url: str,
    admin_credentials: tuple[str, str],
    tmp_path: Path,
) -> str:
    """A freshly signed-in cookie jar, saved for this test only.

    Deliberately *not* session-scoped. F20 says logout invalidates the session
    server-side, and the implementation does it properly — it rotates
    `admin_user.session_token`, which kills every cookie that account has ever
    been issued. A shared login would therefore be destroyed by whichever test
    logs out, and the rest of the run would 401 depending on collection order.
    Only successful logins happen here, so the F17 failure budget is untouched.
    """
    username, password = admin_credentials
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    page.goto("/login")
    page.get_by_label("Логин", exact=True).fill(username)
    page.get_by_label("Пароль", exact=True).fill(password)
    page.get_by_role("button", name="Войти", exact=True).click()
    expect(page.get_by_role("button", name=ru("auth.owner_menu"), exact=True)).to_be_visible()

    path = tmp_path / "admin-state.json"
    context.storage_state(path=str(path))
    context.close()
    return str(path)


@pytest.fixture
def admin_context(new_context, admin_storage_state: str) -> BrowserContext:
    return new_context(storage_state=admin_storage_state)


@pytest.fixture
def admin_page(admin_context: BrowserContext) -> Page:
    return admin_context.new_page()


@pytest.fixture
def admin_api(
    playwright: Playwright, base_url: str, admin_storage_state: str
) -> Iterator[AdminApi]:
    request = playwright.request.new_context(base_url=base_url, storage_state=admin_storage_state)
    try:
        yield AdminApi(request)
    finally:
        request.dispose()


# -------------------------------------------------------------------- clean-up
class Trash:
    """Everything a test created, so teardown can put the database back."""

    def __init__(self, api: AdminApi) -> None:
        self.api = api
        self.albums: list[int] = []
        self.posts: list[int] = []
        self.projects: list[int] = []

    def album(self, album: Album) -> Album:
        self.albums.append(album.id)
        return album

    def album_id(self, album_id: int) -> int:
        self.albums.append(album_id)
        return album_id

    def post(self, post: Post) -> Post:
        self.posts.append(post.id)
        return post

    def post_id(self, post_id: int) -> int:
        self.posts.append(post_id)
        return post_id

    def project_id(self, project_id: int) -> int:
        self.projects.append(project_id)
        return project_id

    def empty(self) -> None:
        for album_id in self.albums:
            self.api.delete_album(album_id)
        for post_id in self.posts:
            self.api.delete_post(post_id)
        for project_id in self.projects:
            self.api.delete_project(project_id)
        self.albums.clear()
        self.posts.clear()
        self.projects.clear()


@pytest.fixture
def trash(admin_api: AdminApi) -> Iterator[Trash]:
    bin_ = Trash(admin_api)
    try:
        yield bin_
    finally:
        bin_.empty()


# ------------------------------------------------------------------- test data
@pytest.fixture
def run_token() -> str:
    return token()


def wait_for_ready(api: AdminApi, album: Album, count: int, timeout_s: float = 180.0) -> None:
    """Block until the pipeline has finished every photo in the album."""
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        ready, waiting = api.ready_count(album)
        if ready >= count and waiting == 0:
            return
        time.sleep(1.0)
    ready, waiting = api.ready_count(album)
    raise AssertionError(
        f"album {album.slug}: {ready}/{count} ready, {waiting} still in flight after {timeout_s}s"
    )


@pytest.fixture
def published_album(admin_api: AdminApi, trash: Trash, run_token: str) -> Album:
    """A published album with four processed photos, built through the API.

    Arranged rather than clicked: a lightbox test that fails because an upload
    failed tells you nothing about the lightbox.
    """
    album = trash.album(admin_api.create_album(f"E2E галерея {run_token}", "Проверка лайтбокса"))
    for index in range(4):
        admin_api.upload_photo(
            album, photo_bytes(1600, 1067, seed=index), f"e2e-{run_token}-{index}.jpg"
        )
    wait_for_ready(admin_api, album, 4)
    admin_api.publish_album(album)
    return album


@pytest.fixture
def published_video_post(admin_api: AdminApi, trash: Trash, run_token: str) -> Post:
    """A published article whose body is a video facade (F63, ADR-035).

    Built for the sweeps rather than for a video test of its own: the play control
    is the newest piece of visible prose, and without a page carrying one, contrast
    in both themes, focus visibility and target size at 360 px would all measure
    everything except it. `e2e/test_video.py` proves what it *does*; these prove it
    can be seen and reached.
    """
    post = trash.post(admin_api.create_post(f"E2E видео свип {run_token}"))
    admin_api.publish_post(post, body_md="Разбор съёмки\n\nhttps://youtu.be/dQw4w9WgXcQ\n")
    return post


@pytest.fixture
def admin_surfaces(
    admin_api: AdminApi, trash: Trash, run_token: str, published_album: Album
) -> list[str]:
    """The signed-in screens, as paths, for the accessibility sweeps.

    Every gate in `test_a11y.py` used to run against anonymous pages, so the
    editor, the photo tile tools, the upload queue and the admin bar — the
    surfaces the product exists to provide — had never been contrast-checked,
    focus-swept or target-measured (UI-AUDIT F-001).

    The album is published rather than draft so the same fixture serves the
    anonymous sweeps; what makes these paths *admin* is the session they are
    opened in, not the state of the content.

    All three rooms of the cabinet join the list rather than replacing anything:
    they exist only for the owner, so no anonymous sweep can ever cover them
    (ADR-029, ADR-036). The draft post created here is one of the things «События»
    lists, so that room is never swept empty; «Сводка» always has figures, and
    «Медиа» always has its «Проверить».
    """
    post = trash.post(admin_api.create_post(f"E2E админ-свип {run_token}"))
    return [
        "/",
        "/dev",
        f"/photo/{published_album.slug}",
        f"/blog/{post.slug}/edit",
        "/me",
        "/me/stats",
        "/me/media",
    ]


@pytest.fixture(scope="session")
def qa_dir() -> Path:
    path = ROOT / "docs" / "qa"
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = ["ru", "wait_for_ready"]
