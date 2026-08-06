"""Launch flow 6 — site-wide search (SPEC F10; user flow 5)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, ru

SEARCH_FIELD = ru("nav.search_label")


@pytest.mark.launch_flow
def test_search_from_the_pill_groups_matches_by_content_type(
    page: Page, base_url: str, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """The test creates everything it looks for; it never searches for
    content another test happened to leave behind."""
    album_title = f"E2E альбом {run_token}"
    post_title = f"E2E статья {run_token}"

    album = trash.album(admin_api.create_album(album_title, "Подпись для поиска"))
    admin_api.publish_album(album)
    post = trash.post(admin_api.create_post(post_title))
    admin_api.publish_post(post, body_md=f"Текст статьи со словом {run_token}.")

    # Typed into the pill and submitted with Enter — no mouse.
    page.goto("/")
    field = page.get_by_role("searchbox", name=SEARCH_FIELD)
    field.focus()
    expect(field).to_be_focused()
    page.keyboard.type(run_token)
    page.keyboard.press("Enter")

    expect(page).to_have_url(f"{base_url}/search?q={run_token}")
    expect(page.get_by_role("heading", level=1)).to_contain_text(run_token)

    # F10: grouped under labelled headings, one group per content type.
    expect(page.get_by_role("heading", name=ru("search.group_posts"))).to_be_visible()
    expect(page.get_by_role("heading", name=ru("search.group_albums"))).to_be_visible()
    expect(page.get_by_role("link", name=post_title)).to_be_visible()
    expect(page.get_by_role("link", name=album_title)).to_be_visible()

    # The result actually goes somewhere.
    page.get_by_role("link", name=album_title).click()
    expect(page.get_by_role("heading", name=album_title, level=1)).to_be_visible()


def test_empty_and_unmatched_queries_have_their_own_states(page: Page, run_token: str) -> None:
    """F10: guidance for an empty query, an explicit dead end for a miss."""
    page.goto("/search")
    expect(page.get_by_text(ru("search.prompt_title"))).to_be_visible()
    expect(page.get_by_text(ru("search.prompt_note"))).to_be_visible()

    page.goto(f"/search?q=нетничего{run_token}")
    expect(page.get_by_text(ru("search.empty_title"))).to_be_visible()


def test_an_unpublished_album_is_absent_from_search(
    page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """F26: publishing is what puts an album into `/photo` *and* into search."""
    album = trash.album(admin_api.create_album(f"E2E черновик {run_token}"))

    page.goto(f"/search?q={run_token}")
    expect(page.get_by_text(ru("search.empty_title"))).to_be_visible()

    admin_api.publish_album(album)
    page.goto(f"/search?q={run_token}")
    expect(page.get_by_role("link", name=album.title)).to_be_visible()
