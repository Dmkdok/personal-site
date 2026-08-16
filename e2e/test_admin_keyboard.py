"""UI-AUDIT F-002 / F-006 — an admin action leaves the caret on a control, and answers.

htmx restores focus after a swap by looking the element up by `id`, which is why
every move button carries one. A `disabled` button cannot take focus and a
deleted one does not exist, so pressing ↑ on the first item — or ★ on the photo
that was already the cover — dropped the caret on `<body>`, and the next Tab
restarted from the skip link at the top of the document. The same branch sent no
`HX-Toast`, so nothing distinguished "already first" from "the request failed".

ADR-016 removed both cases: the controls are never disabled and never withheld,
and the endpoint answers. These are the checks that would have caught it, and
none existed — `grep disabled` over `tests/` and `e2e/` found nothing before this
file, which is the coverage gap F-001 describes.

Pressing ↑ on whatever is already first is a no-op by definition, so these tests
read the current first item out of the page rather than arranging one. They
change nothing, including on a database with the owner's own content in it.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import Album, ru, switch_mode

pytestmark = pytest.mark.a11y


def _press_and_settle(page: Page, element_id: str) -> None:
    """Enter «Правка», focus a control by id, press Enter, and let htmx finish.

    «Правка» first because since ADR-028 these controls are not on the page at
    all in «Просмотр» — and `focus()` on an element with no box does nothing, so
    the caret would land on `<body>` for a reason that has nothing to do with
    what is under test. `switch_mode` is idempotent, so every action can ask.

    Focus is then set through the DOM rather than through Playwright: the caret
    is what is under test, not the pointer. Waiting on `htmx:afterSettle` rather
    than a timeout — focus restoration happens inside the swap, so reading
    `document.activeElement` before it settles measures the wrong moment.
    """
    switch_mode(page, "edit")
    page.evaluate("(id) => document.getElementById(id).focus()", element_id)
    page.evaluate(
        "() => { window.__settled = false;"
        " document.body.addEventListener('htmx:afterSettle',"
        " () => { window.__settled = true; }, { once: true }); }"
    )
    page.keyboard.press("Enter")
    page.wait_for_function("() => window.__settled === true")


def _focused_id(page: Page) -> str:
    """The id of whatever holds the caret — or the tag, so a failure names <body>."""
    return page.evaluate(
        "() => document.activeElement.id || document.activeElement.tagName.toLowerCase()"
    )


def _first_attribute(page: Page, selector: str, attribute: str) -> str:
    value = page.locator(selector).first.get_attribute(attribute)
    assert value, f"no {attribute} on the first {selector}"
    return value


def test_moving_the_first_project_up_keeps_focus_and_says_why(
    admin_page: Page, admin_api, trash, run_token: str
) -> None:
    trash.project_id(admin_api.create_project(f"E2E порядок {run_token}"))
    admin_page.goto("/dev")

    project_id = _first_attribute(admin_page, "li.project", "data-project-id")
    button = f"project-{project_id}-up"

    _press_and_settle(admin_page, button)

    assert _focused_id(admin_page) == button
    expect(admin_page.locator(".toast")).to_have_text(ru("dev.already_first"))


def test_moving_the_first_album_up_keeps_focus_and_says_why(
    admin_page: Page, published_album: Album
) -> None:
    admin_page.goto("/photo")

    album_id = _first_attribute(admin_page, ".album-card", "data-sort-id")
    button = f"album-{album_id}-up"

    _press_and_settle(admin_page, button)

    assert _focused_id(admin_page) == button
    expect(admin_page.locator(".toast")).to_have_text(ru("photo.album_already_first"))


def test_moving_the_first_photo_back_keeps_focus_and_says_why(
    admin_page: Page, published_album: Album
) -> None:
    admin_page.goto(f"/photo/{published_album.slug}")

    photo_id = _first_attribute(admin_page, "li.photo-item", "data-photo-id")
    button = f"photo-{photo_id}-up"

    _press_and_settle(admin_page, button)

    assert _focused_id(admin_page) == button
    expect(admin_page.locator(".toast")).to_have_text(ru("photo.photo_already_first"))


def test_starring_the_current_cover_keeps_focus_and_says_why(
    admin_page: Page, published_album: Album
) -> None:
    """The worst of the three: `{% if ready and not is_cover %}` deleted the button.

    Pressing ★ therefore dropped focus every single time, not only at the ends
    of a list.
    """
    admin_page.goto(f"/photo/{published_album.slug}")

    cover = admin_page.locator("li.photo-item", has=admin_page.locator(".photo-item__cover-flag"))
    photo_id = cover.first.get_attribute("data-photo-id")
    assert photo_id, "the album has no cover — the fixture stopped setting one"
    button = f"photo-{photo_id}-cover"

    _press_and_settle(admin_page, button)

    assert _focused_id(admin_page) == button
    expect(admin_page.locator(".toast")).to_have_text(ru("photo.already_cover"))
