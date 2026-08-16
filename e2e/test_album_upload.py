"""Launch flow 2 — create an album and upload photos (SPEC F21–F26; user flow 8).

Driven entirely through the UI, including the file picker: this is the one test
that has to prove the drop zone, the per-file queue states and the grid's
polling actually work together.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, photo_bytes, ru, switch_mode

PROCESSING_TIMEOUT_MS = 90_000


@pytest.mark.launch_flow
def test_create_album_upload_photos_and_publish(
    admin_page: Page,
    page: Page,
    admin_api: AdminApi,
    trash: Trash,
    run_token: str,
    tmp_path: Path,
) -> None:
    title = f"E2E альбом {run_token}"
    caption = "Загрузка через интерфейс"

    files = []
    for index in range(3):
        path = tmp_path / f"e2e-{run_token}-{index}.jpg"
        path.write_bytes(photo_bytes(1600, 1067, seed=index))
        files.append(str(path))

    # -- F21: create in place on /photo -----------------------------------
    admin_page.goto("/photo")
    # `.first`: with an empty index the invitation in the empty state carries
    # the same label as the toolbar button.
    admin_page.get_by_role("button", name=ru("photo.new_album")).first.click()
    admin_page.get_by_label(ru("photo.title_label"), exact=True).fill(title)
    admin_page.get_by_label(ru("photo.caption_label"), exact=True).fill(caption)
    admin_page.get_by_role("button", name=ru("photo.create_album")).click()

    # The create answers with HX-Redirect straight into the new album.
    expect(admin_page.get_by_role("heading", name=title)).to_be_visible()
    album_id = int(
        admin_page.locator("#upload-zone")
        .get_attribute("data-upload-url")
        .split("/albums/")[1]
        .split("/")[0]
    )
    trash.album_id(album_id)
    slug = admin_page.url.rsplit("/", 1)[-1]

    # A fresh album is a draft: 404 for a visitor (F26).
    assert page.request.get(f"/photo/{slug}").status == 404

    # -- F22: batch upload with per-file state ----------------------------
    admin_page.get_by_label(ru("photo.choose_files_label")).set_input_files(files)

    # `#upload-queue` by id, not by role+name: the «Очередь загрузки» caption is
    # a loose <p>, so the list has no accessible name (T071 finding).
    queue = admin_page.locator("#upload-queue")
    expect(queue.get_by_role("listitem")).to_have_count(3)
    for row in queue.get_by_role("listitem").all():
        expect(row).to_contain_text(ru("photo.state_ready"), timeout=PROCESSING_TIMEOUT_MS)

    # -- F4 / F23: the grid picks the photos up as they become ready ------
    grid = admin_page.get_by_role("list", name=ru("photo.grid_label"))
    expect(grid.get_by_role("listitem")).to_have_count(3, timeout=PROCESSING_TIMEOUT_MS)
    expect(grid.locator('[data-status="ready"]')).to_have_count(3, timeout=PROCESSING_TIMEOUT_MS)

    for image in grid.get_by_role("img").all():
        assert image.get_attribute("loading") == "lazy"
        assert int(image.get_attribute("width")) > 0
        assert int(image.get_attribute("height")) > 0
        assert image.get_attribute("alt")
        assert "640w" in (image.get_attribute("srcset") or "")

    # -- F25: alt text the owner sets is what a visitor reads -------------
    # The tile's tools are the owner's, and since ADR-028 they are on the page
    # in «Правка» only — so entering it is part of the flow, exactly as it is
    # for him. Everything above this line is visible in both modes.
    switch_mode(admin_page, "edit")
    written_alt = f"Тестовый снимок {run_token}"
    first_tile = grid.get_by_role("listitem").first
    first_tile.get_by_label(ru("photo.alt_label")).fill(written_alt)
    first_tile.get_by_label(ru("photo.alt_label")).blur()
    expect(grid.get_by_role("img", name=written_alt)).to_be_visible()

    # -- F26: publish makes it a visitor's album --------------------------
    admin_page.get_by_role("button", name=ru("photo.publish"), exact=True).click()
    expect(admin_page.get_by_role("button", name=ru("photo.unpublish"))).to_be_visible()

    page.goto(f"/photo/{slug}")
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    expect(page.get_by_role("list", name=ru("photo.grid_label")).get_by_role("img")).to_have_count(
        3
    )
    expect(page.get_by_role("img", name=written_alt)).to_be_visible()
    # F36: no editing surface leaks to the visitor.
    expect(page.locator("#upload-zone")).to_have_count(0)

    page.goto("/photo")
    expect(page.get_by_role("link", name=title)).to_be_visible()


def test_a_file_that_is_not_an_image_is_rejected_per_file(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str, tmp_path: Path
) -> None:
    """F24: one rejection is a fact about one row, not about the drop."""
    album = trash.album(admin_api.create_album(f"E2E отбраковка {run_token}"))

    good = tmp_path / f"good-{run_token}.jpg"
    good.write_bytes(photo_bytes(1200, 800, seed=7))
    bad = tmp_path / f"bad-{run_token}.jpg"
    bad.write_bytes(b"this is not an image, whatever the extension says")

    admin_page.goto(f"/photo/{album.slug}")
    admin_page.get_by_label(ru("photo.choose_files_label")).set_input_files([str(good), str(bad)])

    rows = admin_page.locator("#upload-queue").get_by_role("listitem")
    expect(rows).to_have_count(2)
    expect(rows.filter(has_text=ru("photo.state_ready"))).to_have_count(
        1, timeout=PROCESSING_TIMEOUT_MS
    )
    expect(rows.filter(has_text=ru("photo.state_failed"))).to_have_count(1)

    grid = admin_page.get_by_role("list", name=ru("photo.grid_label"))
    expect(grid.get_by_role("listitem")).to_have_count(1, timeout=PROCESSING_TIMEOUT_MS)
