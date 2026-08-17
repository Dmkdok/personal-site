"""UI-AUDIT F-004 — a file that cannot succeed is refused before a byte is sent.

The only client-side gate used to be the file *count*, plus the input's `accept`
attribute — and `accept` does not apply to a drag-and-drop at all. A 60 MB
export, or a TIFF, was therefore uploaded in full, reached 100 % on a real
progress bar, and was only then refused by the server.

The files here are built in the page rather than sent over the wire: a 60 MB
`ArrayBuffer` costs the browser nothing to allocate, and the check under test
reads `File.size` and `File.type`, never the bytes. That also exercises the
*drop* path specifically, which is the one `accept` never covered.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import AdminApi, ru, switch_mode

pytestmark = pytest.mark.a11y

MEGABYTE = 1024 * 1024

# `items.add` is what populates `dataTransfer.files`, which is what the drop
# handler reads. Dispatching on the zone rather than calling the handler keeps
# the test on the same path a real drop takes.
DROP_FILES = """
(specs) => {
  const transfer = new DataTransfer();
  for (const spec of specs) {
    transfer.items.add(
      new File([new ArrayBuffer(spec.size)], spec.name, { type: spec.type })
    );
  }
  document.getElementById('upload-zone').dispatchEvent(
    new DragEvent('drop', { dataTransfer: transfer, bubbles: true, cancelable: true })
  );
}
"""


@pytest.fixture
def album_page(admin_page: Page, admin_api: AdminApi, trash, run_token: str) -> Page:
    """An album open in «Правка», which is where the owner uploads.

    Since I5 the upload zone is not on the page in «Просмотр» at all (ADR-032),
    so entering the mode is part of the flow rather than a detail of the test —
    the drop below then lands on the zone the owner is actually looking at.
    """
    album = trash.album(admin_api.create_album(f"E2E предпроверка {run_token}"))
    admin_page.goto(f"/photo/{album.slug}")
    switch_mode(admin_page, "edit")
    return admin_page


def test_files_that_cannot_succeed_never_reach_the_network(album_page: Page) -> None:
    uploads: list[str] = []
    album_page.on(
        "request",
        lambda request: (
            uploads.append(request.url)
            if request.method == "POST" and "/photos" in request.url
            else None
        ),
    )

    album_page.evaluate(
        DROP_FILES,
        [
            {"name": "экспорт.jpg", "type": "image/jpeg", "size": 60 * MEGABYTE},
            {"name": "скан.tiff", "type": "image/tiff", "size": 4096},
        ],
    )

    rows = album_page.locator(".upload-item")
    expect(rows).to_have_count(2)
    expect(rows.nth(0)).to_have_class("upload-item upload-item--failed")
    expect(rows.nth(1)).to_have_class("upload-item upload-item--failed")

    expect(rows.nth(0).locator(".upload-item__error")).to_have_text(
        ru("photo.file_too_big").replace("{limit}", "50")
    )
    expect(rows.nth(1).locator(".upload-item__error")).to_have_text(ru("photo.file_wrong_type"))

    assert uploads == [], uploads


def test_the_gate_only_refuses_what_the_server_would(album_page: Page) -> None:
    """A positive control: a gate that refuses everything would pass the test above.

    The bytes here are zeros, so the server rejects the frame on decode — which
    is the point. What is being proved is that the request left the browser.
    """
    uploads: list[str] = []
    album_page.on(
        "request",
        lambda request: (
            uploads.append(request.url)
            if request.method == "POST" and "/photos" in request.url
            else None
        ),
    )

    album_page.evaluate(DROP_FILES, [{"name": "снимок.jpg", "type": "image/jpeg", "size": 4096}])

    expect(album_page.locator(".upload-item")).to_have_count(1)
    album_page.wait_for_timeout(1500)
    assert len(uploads) == 1, uploads


def test_a_heic_from_a_phone_is_not_turned_away_at_the_door(album_page: Page) -> None:
    """T121 taught the server HEIC; the gate in front of it must agree (F51).

    Two shapes, because browsers disagree about this format: one reports
    `image/heic`, another reports nothing at all and leaves the type to the
    extension — which the gate deliberately lets through, since the server reads
    the magic bytes. Zeros again: the server refuses these on decode, and what
    is under test is that they were sent to it rather than refused here.
    """
    uploads: list[str] = []
    album_page.on(
        "request",
        lambda request: (
            uploads.append(request.url)
            if request.method == "POST" and "/photos" in request.url
            else None
        ),
    )

    album_page.evaluate(
        DROP_FILES,
        [
            {"name": "IMG_0042.HEIC", "type": "image/heic", "size": 4096},
            {"name": "IMG_0043.heic", "type": "", "size": 4096},
        ],
    )

    rows = album_page.locator(".upload-item")
    expect(rows).to_have_count(2)
    album_page.wait_for_timeout(1500)

    assert len(uploads) == 2, uploads
    # And no row was failed by *this* gate — whatever the server then says about
    # four kilobytes of zeros is the server's own answer.
    expect(album_page.get_by_text(ru("photo.file_wrong_type"))).to_have_count(0)

    # The dialog offers them too: `accept` carries the extensions as well,
    # because a filter that recognises neither the type nor the suffix hides the
    # phone's photographs instead of showing them.
    accept = album_page.locator("#upload-input").get_attribute("accept") or ""
    assert ".heic" in accept and ".heif" in accept, accept
    assert "image/heic" in accept, accept


def test_a_running_batch_can_be_stopped(album_page: Page) -> None:
    """Fifty files used to be a commitment: `pending` and the three live
    XMLHttpRequests had no abort path at all."""
    cancel = album_page.locator("#upload-queue-cancel")
    expect(cancel).to_be_hidden()

    album_page.evaluate(
        DROP_FILES,
        [{"name": f"кадр-{i}.jpg", "type": "image/jpeg", "size": 2 * MEGABYTE} for i in range(12)],
    )

    expect(cancel).to_be_visible()
    cancel.click()

    expect(album_page.locator(".upload-item--failed").first).to_be_visible()
    expect(cancel).to_be_hidden()
    # Every row that was stopped offers another attempt without re-picking it.
    expect(album_page.locator(".upload-item__retry").first).to_have_text(ru("photo.retry_upload"))
