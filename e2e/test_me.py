"""F62 / F64 — the cabinet gathers what needs the owner, in rooms of its own.

The gap in-place editing cannot close is state that is not on the page you are
looking at: a draft is visible only on `/blog`, an unpublished album only on
`/photo`, a photograph that failed to process only inside its own album. The
cabinet answers that — and, since ADR-036, two more questions that have no place
on the site itself: how much there is of everything, and what is in the storage.
It authors nothing; the editing surface does not move.

To anyone without a session no room's address exists, which is the same treatment
a draft article gets: a redirect to `/login` would confirm the page is there.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.conftest import Trash, wait_for_ready
from e2e.helpers import AdminApi, open_owner_menu, photo_bytes, ru


def test_no_room_exists_for_a_visitor(page: Page) -> None:
    for address in ("/me", "/me/stats", "/me/media", "/me/media/orphans"):
        assert page.request.get(address).status == 404, address

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
    # The photograph is ready and nobody has described it, and «События» says
    # nothing about it: a missing description is a hint in the album, in «Правка»,
    # not a task in the cabinet (ADR-036). It used to be listed here, and on real
    # data that section was two dozen rows that all read the same.
    expect(
        admin_page.get_by_role("link", name=ru("me.photo_in", album=album.title), exact=True)
    ).to_have_count(0)

    # Every answer leads to the page that edits it, which is the whole claim.
    draft.click()
    admin_page.wait_for_url(f"**/blog/{post.slug}/edit")


def test_every_room_is_an_address_of_its_own(admin_page: Page) -> None:
    """F64: the menu walks the rooms, and the browser knows where it has been.

    Reached by link and left by the back button — which is what «its own address»
    buys and what tabs swapped on one route would have cost (ADR-036).
    """
    admin_page.goto("/me")

    for label, path in (
        (ru("me.room_stats"), "/me/stats"),
        (ru("me.room_media"), "/me/media"),
        (ru("me.room_events"), "/me"),
    ):
        admin_page.get_by_role("link", name=label, exact=True).click()
        admin_page.wait_for_url(f"**{path}")
        expect(admin_page.get_by_role("link", name=label, exact=True)).to_have_attribute(
            "aria-current", "page"
        )

    admin_page.go_back()
    admin_page.wait_for_url("**/me/media")


def test_the_disk_is_walked_only_when_the_owner_asks(admin_page: Page) -> None:
    """ADR-037: «Медиа» opens without touching the storage it describes.

    The region is empty on load — nothing has been walked — and the press fills
    it. A room that scanned on load would be the cabinet's slowest page and its
    front door at the same time, on the one screen that has to work when
    something is wrong with the disk.
    """
    admin_page.goto("/me/media")

    report = admin_page.locator("#orphan-report")
    expect(report).to_be_empty()

    admin_page.get_by_role("button", name=ru("me.disk_check"), exact=True).click()

    expect(report).to_contain_text("Файлов —")
    # It reports and never offers: deleting stays a command on the server.
    expect(report).to_contain_text("--prune")


def test_the_disk_section_clears_the_empty_room_above_it(admin_page: Page) -> None:
    """T141: `.empty` and a real group give the disk section the same gap.

    Nothing is in flight and nothing has failed, so «Медиа» renders the shared
    `.empty` box instead of a `.cabinet__group` — and `.cabinet__group +
    .cabinet__group` (me.css) never matches that pair. The disk section still
    needs `--space-l` of clearance above `.empty`'s dashed border, exactly as it
    gets above a real group.
    """
    admin_page.goto("/me/media")

    empty = admin_page.locator(".empty")
    disk = admin_page.locator(".cabinet__disk")
    expect(empty).to_be_visible()
    expect(disk).to_be_visible()

    space_l = admin_page.evaluate(
        """() => {
            const root = document.documentElement;
            const raw = getComputedStyle(root).getPropertyValue('--space-l');
            return parseFloat(raw) * parseFloat(getComputedStyle(root).fontSize);
        }"""
    )

    empty_box = empty.bounding_box()
    disk_box = disk.bounding_box()
    assert empty_box is not None
    assert disk_box is not None

    gap = disk_box["y"] - (empty_box["y"] + empty_box["height"])
    assert gap >= space_l - 1, (gap, space_l)


def test_no_room_is_ever_indexed(admin_page: Page) -> None:
    """All three, because all three extend the same layout — asserted, not assumed."""
    for room in ("/me", "/me/stats", "/me/media"):
        admin_page.goto(room)
        robots_meta = admin_page.locator('meta[name="robots"]').get_attribute("content")
        assert robots_meta == "noindex, nofollow", (room, robots_meta)

    # One prefix rule covers the three, which is why `seo.py` did not change.
    assert "Disallow: /me" in admin_page.request.get("/robots.txt").text()
