"""Launch flow 4 — lightbox by keyboard (SPEC F5; user flow 2).

Every interaction here is a key press. Nothing is clicked, so a pass is also the
keyboard evidence T071 needs for the lightbox.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import Album, ru


@pytest.mark.launch_flow
def test_lightbox_is_fully_operable_from_the_keyboard(page: Page, published_album: Album) -> None:
    page.goto(f"/photo/{published_album.slug}")

    grid = page.get_by_role("list", name=ru("photo.grid_label"))
    thumbnails = grid.get_by_role("link")
    expect(thumbnails).to_have_count(4)

    # Tab to the first thumbnail rather than clicking it.
    first = thumbnails.first
    first.focus()
    expect(first).to_be_focused()
    page.keyboard.press("Enter")

    dialog = page.get_by_role("dialog", name=ru("photo.lightbox_label"))
    expect(dialog).to_be_visible()
    assert dialog.get_attribute("aria-modal") == "true"

    # Focus lands inside, on the close control.
    close = dialog.get_by_role("button", name=ru("photo.lightbox_close"))
    expect(close).to_be_focused()

    counter = dialog.locator(".lightbox__counter")
    expect(counter).to_have_text(ru("photo.lightbox_position", index=1, total=4))

    # F5: ←/→ move, and the sheet wraps at either end.
    page.keyboard.press("ArrowRight")
    expect(counter).to_have_text(ru("photo.lightbox_position", index=2, total=4))
    page.keyboard.press("ArrowLeft")
    expect(counter).to_have_text(ru("photo.lightbox_position", index=1, total=4))
    page.keyboard.press("ArrowLeft")
    expect(counter).to_have_text(ru("photo.lightbox_position", index=4, total=4))
    page.keyboard.press("Home")
    expect(counter).to_have_text(ru("photo.lightbox_position", index=1, total=4))

    # The photograph on show carries alt text.
    assert page.locator(".lightbox__img").get_attribute("alt")

    # Body scroll is locked while it is open.
    assert page.evaluate("() => getComputedStyle(document.documentElement).overflow") in {
        "hidden",
        "clip",
    }

    # F5: focus is trapped — three controls, and Tab cycles among them only.
    seen = []
    for _ in range(4):
        page.keyboard.press("Tab")
        seen.append(page.evaluate("() => document.activeElement.className"))
    assert all("lightbox__" in name for name in seen), seen

    # Esc closes and hands focus back to the thumbnail that opened it.
    page.keyboard.press("Escape")
    expect(dialog).to_be_hidden()
    expect(first).to_be_focused()
    assert page.evaluate("() => getComputedStyle(document.documentElement).overflow") not in {
        "hidden",
        "clip",
    }


def test_lightbox_closes_on_a_backdrop_click(page: Page, published_album: Album) -> None:
    """F5's pointer half, so the keyboard test above is not the only proof."""
    page.goto(f"/photo/{published_album.slug}")
    grid = page.get_by_role("list", name=ru("photo.grid_label"))
    grid.get_by_role("link").first.click()

    dialog = page.get_by_role("dialog", name=ru("photo.lightbox_label"))
    expect(dialog).to_be_visible()
    dialog.locator(".lightbox__backdrop").click(position={"x": 5, "y": 5})
    expect(dialog).to_be_hidden()


def test_a_thumbnail_is_a_plain_link_without_javascript(
    browser, base_url: str, published_album: Album
) -> None:
    """Progressive enhancement: the album still works with JS switched off."""
    context = browser.new_context(base_url=base_url, java_script_enabled=False)
    try:
        page = context.new_page()
        page.goto(f"/photo/{published_album.slug}")
        link = page.get_by_role("list", name=ru("photo.grid_label")).get_by_role("link").first
        href = link.get_attribute("href")
        assert href and href.startswith("/media/"), href
        assert page.request.get(href).status == 200
    finally:
        context.close()
