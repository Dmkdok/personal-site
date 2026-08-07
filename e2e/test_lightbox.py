"""Launch flow 4 — lightbox by keyboard (SPEC F5; user flow 2).

Every interaction here is a key press. Nothing is clicked, so a pass is also the
keyboard evidence T071 needs for the lightbox.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import Trash, wait_for_ready
from e2e.helpers import AdminApi, Album, photo_bytes, ru


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


# --------------------------------------------------------------------------
# T080 — the open photograph must fit the screen.
#
# It did not. `.lightbox__figure` was sized by its content, so `max-block-size:
# 100%` on the image had nothing to resolve against and the picture kept its
# full aspect height: a 4000×6000 portrait rendered 1328×1992 inside a 900 px
# viewport, centred, so only its middle was ever visible. Small test photographs
# hid it — the shapes below are the ones that actually break.
# --------------------------------------------------------------------------
SHAPES = {"landscape": (6000, 4000), "portrait": (4000, 6000), "panorama": (6000, 1500)}
VIEWPORTS = [(1440, 900), (360, 740), (1920, 1080)]


@pytest.fixture
def oversized_album(admin_api: AdminApi, trash: Trash, run_token: str) -> Album:
    """An album of 6000 px photographs — landscape, portrait and panorama."""
    album = trash.album(admin_api.create_album(f"E2E крупные {run_token}"))
    for name, (width, height) in SHAPES.items():
        admin_api.upload_photo(
            album, photo_bytes(width, height, seed=width), f"e2e-{run_token}-{name}.jpg"
        )
    wait_for_ready(admin_api, album, len(SHAPES))
    admin_api.publish_album(album)
    return album


MEASURE = """() => {
    const img = document.querySelector('.lightbox__img');
    const box = img.getBoundingClientRect();
    return {
      w: Math.round(box.width), h: Math.round(box.height),
      left: Math.round(box.left), top: Math.round(box.top),
      vw: window.innerWidth, vh: window.innerHeight,
      docScroll: document.querySelector('.lightbox').scrollWidth,
      picked: img.currentSrc,
    };
}"""


@pytest.mark.parametrize(("width", "height"), VIEWPORTS)
def test_an_open_photograph_never_exceeds_the_viewport(
    page: Page, oversized_album: Album, width: int, height: int
) -> None:
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"/photo/{oversized_album.slug}")

    thumbnails = page.get_by_role("list", name=ru("photo.grid_label")).get_by_role("link")
    expect(thumbnails).to_have_count(len(SHAPES))

    for index in range(len(SHAPES)):
        thumbnails.nth(index).click()
        dialog = page.get_by_role("dialog", name=ru("photo.lightbox_label"))
        expect(dialog).to_be_visible()
        expect(page.locator(".lightbox__img")).to_have_js_property("complete", True)

        m = page.evaluate(MEASURE)
        shape = list(SHAPES)[index]
        assert m["w"] <= m["vw"], f"{shape} at {width}×{height}: {m['w']}px wide in {m['vw']}px"
        assert m["h"] <= m["vh"], f"{shape} at {width}×{height}: {m['h']}px tall in {m['vh']}px"
        assert m["left"] >= 0 and m["top"] >= 0, (
            f"{shape} at {width}×{height}: {m} spills off-screen"
        )
        assert m["docScroll"] <= m["vw"], (
            f"{shape} at {width}×{height}: the overlay scrolls sideways"
        )

        page.keyboard.press("Escape")
        expect(dialog).to_be_hidden()


def test_the_rendition_fetched_matches_the_size_it_is_drawn_at(
    page: Page, oversized_album: Album
) -> None:
    """`sizes` was a flat `100vw`, three times the truth for a portrait shot.

    The preloader made it worse: it fetched `data-src` — always the largest
    rendition — so the neighbour arrived at 2560 px and the browser reused that
    cached candidate rather than the one it would otherwise have chosen.
    """
    page.set_viewport_size({"width": 360, "height": 740})
    page.goto(f"/photo/{oversized_album.slug}")

    thumbnails = page.get_by_role("list", name=ru("photo.grid_label")).get_by_role("link")
    # The third shot: its neighbours have been preloaded by the time it opens.
    thumbnails.nth(2).click()
    expect(page.get_by_role("dialog", name=ru("photo.lightbox_label"))).to_be_visible()
    expect(page.locator(".lightbox__img")).to_have_js_property("complete", True)

    m = page.evaluate(MEASURE)
    picked = int(re.search(r"_(\d+)\.webp", m["picked"]).group(1))
    # 640 is the smallest rendition; on a 360 px phone nothing bigger is needed.
    assert picked == 640, f"drawn {m['w']}px wide but fetched the {picked}px rendition"
