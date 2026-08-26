"""F38 in the form I5 gives it — the editor says how the markup works (T139).

The vocabulary was always there and never discoverable: nobody guesses `{.wide}`,
and T138 added a video form with no markup of its own at all. So the disclosure
under the textarea lists every shape the renderer understands, and the toolbar
grew the two buttons that write the shapes a person would otherwise have to
remember — a video's own paragraph and a table's three rows.

What is asserted here is that pressing a button leaves *working* Markdown in the
textarea, not that a button exists: an inserted skeleton that does not render is
worse than no button, because the owner finds out in the preview.
"""

from __future__ import annotations

import json

from playwright.sync_api import Page, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, ru


def test_the_sheet_is_closed_until_it_is_asked_for(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    post = trash.post(admin_api.create_post(f"E2E шпаргалка {run_token}"))
    admin_page.goto(f"/blog/{post.slug}/edit")

    summary = admin_page.get_by_text(ru("blog.md.size_summary"), exact=True)
    expect(summary).to_be_visible()

    # Closed by default, and the state is not remembered: a reload finds it closed
    # again, which is the whole reason it costs nothing once it has been read.
    row = admin_page.get_by_text(ru("blog.md.sheet_strike_text"), exact=False)
    expect(row).to_be_hidden()

    summary.click()
    expect(row).to_be_visible()

    admin_page.reload()
    expect(admin_page.get_by_text(ru("blog.md.sheet_strike_text"), exact=False)).to_be_hidden()


def test_the_sheet_covers_every_shape_the_renderer_understands(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    post = trash.post(admin_api.create_post(f"E2E шпаргалка полная {run_token}"))
    admin_page.goto(f"/blog/{post.slug}/edit")
    admin_page.get_by_text(ru("blog.md.size_summary"), exact=True).click()

    sheet = admin_page.locator(".editor__details", has_text=ru("blog.md.size_summary"))
    for key in (
        "size_normal_code",
        "size_wide_code",
        "size_full_code",
        "size_caption_code",
        "sheet_video_code",
        "sheet_table_code",
        "sheet_quote_code",
        "sheet_code_code",
        "sheet_link_code",
        "sheet_list_code",
        "sheet_heading_code",
        "sheet_strike_code",
    ):
        # `to_contain_text` normalises whitespace, which is what makes the two
        # multi-line snippets comparable to their catalogue strings.
        expect(sheet).to_contain_text(ru(f"blog.md.{key}").split("\n")[0])


def test_the_video_button_writes_a_captioned_paragraph_of_its_own(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """The shape `render_markdown` turns into a player, and nothing less (F63).

    A video link among other text is an ordinary link, so a button that dropped
    the address at the caret would produce something that looks inserted and does
    not play.

    T142 changed what the button writes — a bare address used to leave every
    video anonymous until the author knew to wrap it. It now inserts the
    captioned form `_video_paragraph` already turns into a `<figcaption>`, with
    the caption selected so typing over it is the next thing that happens. This
    assertion changed under T142 for exactly that reason, named rather than
    quiet, per the regression contract.
    """
    post = trash.post(admin_api.create_post(f"E2E кнопка видео {run_token}"))
    admin_page.goto(f"/blog/{post.slug}/edit")

    body = admin_page.locator("#post-body")
    body.fill("Первый абзац.")
    body.click()
    admin_page.keyboard.press("Control+End")

    admin_page.get_by_role("button", name=ru("blog.md.video"), exact=True).click()

    text = body.input_value()
    assert text.startswith("Первый абзац.")
    caption = ru("blog.md.ph_video_text")
    address = ru("blog.md.ph_video_url")
    assert text.endswith("\n\n[" + caption + "](" + address + ")"), repr(text)
    # The caption is selected, so typing a real title replaces the placeholder
    # immediately — the address is filled in afterward.
    assert (
        admin_page.evaluate(
            "() => { const a = document.getElementById('post-body');"
            " return a.value.slice(a.selectionStart, a.selectionEnd); }"
        )
        == caption
    )


def test_a_link_pasted_over_the_selected_caption_still_becomes_a_player(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """F66, ADR-040 — the direct gesture the button invites must not produce a dead link.

    videoAction() leaves the *caption* selected (T142), so pressing the button
    and immediately pasting the address already on the clipboard — the most
    direct thing to do — lands the address in the caption slot, not the
    address slot. `maybeFillVideoCaption` (`editor.js`) has to recognise that
    shape too and put the address back where a player is built from it,
    server-fetched title and all — found by Run 8's review as a High, fixed
    in the same session.
    """
    post = trash.post(admin_api.create_post(f"E2E видео мимо подписи {run_token}"))
    admin_page.goto(f"/blog/{post.slug}/edit")

    admin_page.route(
        "**/blog/admin/video-title",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"title": "Название с сервиса"}),
        ),
    )

    body = admin_page.locator("#post-body")
    body.click()
    admin_page.get_by_role("button", name=ru("blog.md.video"), exact=True).click()

    # The caption is selected; paste the address straight over it, exactly as
    # a real paste would leave the value and the caret — no native clipboard
    # needed to prove what the listener does with the result.
    url = "https://youtu.be/dQw4w9WgXcQ"
    admin_page.evaluate(
        """(url) => {
            const area = document.getElementById('post-body');
            const start = area.selectionStart, end = area.selectionEnd;
            area.value = area.value.slice(0, start) + url + area.value.slice(end);
            const caret = start + url.length;
            area.setSelectionRange(caret, caret);
            area.dispatchEvent(new Event('paste', { bubbles: true }));
        }""",
        url,
    )

    expect(body).to_have_value("[Название с сервиса](" + url + ")")


def test_a_link_pasted_into_the_address_slot_fills_the_caption(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """The flow T142 was written for: type over the selected caption, tab to
    the address, paste the link there — still fetches and fills the caption,
    exactly as when the paste lands the other way round.
    """
    post = trash.post(admin_api.create_post(f"E2E видео в адрес {run_token}"))
    admin_page.goto(f"/blog/{post.slug}/edit")

    admin_page.route(
        "**/blog/admin/video-title",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"title": "Название с сервиса"}),
        ),
    )

    body = admin_page.locator("#post-body")
    body.click()
    admin_page.get_by_role("button", name=ru("blog.md.video"), exact=True).click()

    # Move the caret into the address slot — the caption stays the untouched
    # placeholder — then paste there.
    url = "https://youtu.be/dQw4w9WgXcQ"
    admin_page.evaluate(
        """(url) => {
            const area = document.getElementById('post-body');
            const value = area.value;
            const open = value.lastIndexOf('(');
            const close = value.lastIndexOf(')');
            area.value = value.slice(0, open + 1) + url + value.slice(close);
            const caret = open + 1 + url.length;
            area.setSelectionRange(caret, caret);
            area.dispatchEvent(new Event('paste', { bubbles: true }));
        }""",
        url,
    )

    expect(body).to_have_value("[Название с сервиса](" + url + ")")


def test_the_table_button_writes_a_table_that_renders(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    post = trash.post(admin_api.create_post(f"E2E кнопка таблицы {run_token}"))
    admin_page.goto(f"/blog/{post.slug}/edit")

    body = admin_page.locator("#post-body")
    body.click()
    admin_page.get_by_role("button", name=ru("blog.md.table"), exact=True).click()

    text = body.input_value()
    header, dashes, row = text.strip().split("\n")
    assert header == f"| {ru('blog.md.ph_th')} | {ru('blog.md.ph_th')} |", header
    assert dashes == "| --- | --- |", dashes
    assert row == f"| {ru('blog.md.ph_td')} | {ru('blog.md.ph_td')} |", row

    # And it is a table on the page, not three lines that look like one: the
    # preview is the same `render_markdown` the published article goes through.
    expect(admin_page.locator("#preview-body table")).to_have_count(1)
