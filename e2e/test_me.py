"""F62 / ADR-029 — the cabinet gathers what needs the owner onto one screen.

The gap in-place editing cannot close is state that is not on the page you are
looking at: a draft is visible only on `/blog`, an unpublished album only on
`/photo`, a photograph nobody described only inside its own album. The cabinet
answers one question — what needs attention — and links every answer back to the
page that edits it. It authors nothing; the editing surface does not move.

To anyone without a session the address does not exist, which is the same
treatment a draft article gets: a redirect to `/login` would confirm the page is
there.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.conftest import Trash, wait_for_ready
from e2e.helpers import AdminApi, open_owner_menu, photo_bytes, ru


def test_the_address_does_not_exist_for_a_visitor(page: Page) -> None:
    assert page.request.get("/me").status == 404

    page.goto("/")
    expect(page.get_by_role("link", name=ru("me.title"), exact=True)).to_have_count(0)


def test_the_owner_reaches_the_cabinet_from_the_menu(admin_page: Page) -> None:
    admin_page.goto("/")
    open_owner_menu(admin_page).get_by_role("link", name=ru("me.title"), exact=True).click()

    expect(admin_page.get_by_role("heading", name=ru("me.title"))).to_be_visible()
    assert admin_page.url.endswith("/me")


def test_the_cabinet_finds_everything_on_one_screen(
    admin_page: Page,
    admin_api: AdminApi,
    trash: Trash,
    run_token: str,
) -> None:
    """One visit, four sections, none of them opened in its own part of the site."""
    album = trash.album(admin_api.create_album(f"E2E кабинет альбом {run_token}"))
    admin_api.upload_photo(album, photo_bytes(1200, 800, seed=5), f"e2e-{run_token}.jpg")
    wait_for_ready(admin_api, album, 1)

    post = trash.post(admin_api.create_post(f"E2E кабинет черновик {run_token}"))
    project_title = f"E2E кабинет проект {run_token}"
    trash.project_id(admin_api.create_project(project_title))

    admin_page.goto("/me")

    draft = admin_page.get_by_role("link", name=post.title, exact=True)
    expect(draft).to_be_visible()
    expect(admin_page.get_by_role("link", name=album.title, exact=True)).to_be_visible()
    expect(admin_page.get_by_role("link", name=project_title, exact=True)).to_be_visible()
    # The photograph is ready and nobody has described it — the album's own
    # fallback alt is a floor, not a description (UI-AUDIT F-017).
    expect(
        admin_page.get_by_role("link", name=ru("me.photo_in", album=album.title), exact=True)
    ).to_be_visible()

    # Every answer leads to the page that edits it, which is the whole claim.
    draft.click()
    admin_page.wait_for_url(f"**/blog/{post.slug}/edit")


def test_the_cabinet_is_never_indexed(admin_page: Page) -> None:
    admin_page.goto("/me")
    robots_meta = admin_page.locator('meta[name="robots"]').get_attribute("content")
    assert robots_meta == "noindex, nofollow", robots_meta

    assert "Disallow: /me" in admin_page.request.get("/robots.txt").text()
