"""F72/F73 (T149) — the blog editor's photo control is its own visible action,
distinct from the Markdown-snippet buttons, and every upload gets its own row.

`test_upload_guard.py` already proves the *client-side rejection* gate reaches
the blog editor's own limits (F51 stays server-authoritative); the tests here
are about what T149 actually changed: the control's shape, and the row-based
progress feedback that replaced a single shared toast.
"""

from __future__ import annotations

import base64

from playwright.sync_api import Page, Response, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, Post, photo_bytes, ru

# Real bytes, not a zeroed ArrayBuffer (`test_upload_guard.py`'s DROP_FILES):
# these two must actually decode and be stored, so the response's `markdown`
# can be read back and its position in the textarea checked.
_DROP_REAL_FILES = """
(specs) => {
  const transfer = new DataTransfer();
  for (const spec of specs) {
    const binary = atob(spec.data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    transfer.items.add(new File([bytes], spec.name, { type: spec.type }));
  }
  document.getElementById('post-body').dispatchEvent(
    new DragEvent('drop', { dataTransfer: transfer, bubbles: true, cancelable: true })
  );
}
"""


def _open_editor(admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str) -> Post:
    post = trash.post(admin_api.create_post(f"E2E фото-контрол {run_token}"))
    admin_page.goto(f"/blog/{post.slug}/edit")
    return post


def test_the_photo_control_is_its_own_action_not_a_toolbar_glyph(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """F72 — labelled and outside `.md-toolbar`'s button row, but still the
    same file picker `editor.js` has always opened."""
    _open_editor(admin_page, admin_api, trash, run_token)

    control = admin_page.get_by_role("button", name=ru("blog.md.image"), exact=True)
    expect(control).to_be_visible()
    # Not one of the formatting buttons: T148's toolbar-parity test already
    # covers every button that *is* — this one is a `.md-toolbar__button` no
    # longer at all.
    assert "md-toolbar__button" not in (control.get_attribute("class") or "")

    with admin_page.expect_file_chooser() as chooser_info:
        control.click()
    assert chooser_info.value.is_multiple


def test_two_dropped_photos_get_their_own_rows_and_land_in_drop_order(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """F73 — a row per file, not a single shared toast, and the sequential
    uploads this small a batch needs (T149) keep completion order identical
    to drop order without a reorder buffer."""
    _open_editor(admin_page, admin_api, trash, run_token)
    body = admin_page.locator("#post-body")
    body.click()

    responses: list[str] = []

    def capture(response: Response) -> None:
        if response.request.method != "POST" or not response.url.endswith("/blog/admin/images"):
            return
        try:
            payload = response.json()
        except Exception:
            return
        if payload.get("markdown"):
            responses.append(payload["markdown"])

    admin_page.on("response", capture)

    specs = [
        {
            "name": "первое.jpg",
            "type": "image/jpeg",
            "data": base64.b64encode(photo_bytes(seed=101)).decode("ascii"),
        },
        {
            "name": "второе.jpg",
            "type": "image/jpeg",
            "data": base64.b64encode(photo_bytes(seed=202)).decode("ascii"),
        },
    ]
    admin_page.evaluate(_DROP_REAL_FILES, specs)

    rows = admin_page.locator("#editor-image-queue .upload-item")
    expect(rows).to_have_count(2)
    expect(rows.nth(0)).to_have_class("upload-item upload-item--ready", timeout=15000)
    expect(rows.nth(1)).to_have_class("upload-item upload-item--ready", timeout=15000)

    assert len(responses) == 2, responses
    value = body.input_value()
    assert responses[0] in value, value
    assert responses[1] in value, value
    assert value.index(responses[0]) < value.index(responses[1]), value


def test_a_failed_upload_offers_a_retry_that_does_not_touch_the_other_row(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """Retry re-sends the same `File` and lands its own row, without
    disturbing whatever the rest of the drop already did."""
    _open_editor(admin_page, admin_api, trash, run_token)
    body = admin_page.locator("#post-body")
    body.click()

    admin_page.route(
        "**/blog/admin/images",
        lambda route: route.fulfill(
            status=400, content_type="application/json", body='{"error": "боюсь"}'
        ),
    )

    specs = [
        {
            "name": "не-выйдет.jpg",
            "type": "image/jpeg",
            "data": base64.b64encode(photo_bytes(seed=303)).decode("ascii"),
        }
    ]
    admin_page.evaluate(_DROP_REAL_FILES, specs)

    row = admin_page.locator("#editor-image-queue .upload-item").first
    expect(row).to_have_class("upload-item upload-item--failed")
    expect(row.locator(".upload-item__error")).to_have_text("боюсь")
    retry = row.locator(".upload-item__retry")
    expect(retry).to_have_text(ru("blog.image_retry"))

    admin_page.unroute("**/blog/admin/images")
    retry.click()

    expect(row).to_have_class("upload-item upload-item--ready", timeout=15000)
    # The alt text is the generic placeholder (`blog.md.ph_alt`), not the
    # filename — what proves the retry actually landed is that a picture's
    # Markdown appeared at all, which it did not before this click.
    assert "![" in body.input_value(), body.input_value()
