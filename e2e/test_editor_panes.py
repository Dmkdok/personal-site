"""F75 (T150) — below 60rem, source and preview are a press apart.

Both editor panes render full height (`.editor__textarea`'s 22rem minimum
plus the toolbar, the photo control on the blog editor, and the cheat
sheet), so on a narrow viewport reaching the preview meant scrolling past
all of it. `.editor__pane-switch` swaps which pane is shown instead; at the
existing 60rem breakpoint the switch is hidden and the layout is the
unchanged two-column desktop one, proven here at the default (1280-wide,
well above 60rem) viewport the other editor tests already run at.

Visibility is asserted on the `.editor__pane` section rather than the
`#preview-body`/`#shared-preview-body` div it wraps: that div is empty on a
freshly created article, and an empty element with no box of its own is
"hidden" to Playwright regardless of its ancestor's `display` — the section
around it always has a border, padding and a heading, so its own box size
is what the switch actually controls.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, SharedArticle, ru

_NARROW = {"width": 360, "height": 780}


def test_the_narrow_switch_reaches_the_preview_without_scrolling_past_the_textarea(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    post = trash.post(admin_api.create_post(f"E2E панель переключения {run_token}"))
    admin_page.set_viewport_size(_NARROW)
    admin_page.goto(f"/blog/{post.slug}/edit")

    body = admin_page.locator("#post-body")
    preview_pane = admin_page.locator(".editor__pane.editor__preview")
    source_button = admin_page.get_by_role("button", name=ru("blog.pane_source"), exact=True)
    preview_button = admin_page.get_by_role("button", name=ru("blog.pane_preview"), exact=True)

    # The switch itself is reachable, and starts on the source — the same
    # pane a visitor to this page sees first today.
    expect(source_button).to_be_visible()
    expect(preview_button).to_be_visible()
    expect(source_button).to_have_attribute("aria-pressed", "true")
    expect(preview_button).to_have_attribute("aria-pressed", "false")
    expect(body).to_be_visible()
    expect(preview_pane).to_be_hidden()

    preview_button.click()

    expect(preview_button).to_have_attribute("aria-pressed", "true")
    expect(source_button).to_have_attribute("aria-pressed", "false")
    # Not merely present in the DOM — actually reachable without a scroll,
    # which is the whole point of F75.
    expect(preview_pane).to_be_visible()
    expect(preview_pane).to_be_in_viewport()
    expect(body).to_be_hidden()

    # And back — the switch works both ways, off the DOM state alone.
    source_button.click()
    expect(body).to_be_visible()
    expect(preview_pane).to_be_hidden()


def test_the_narrow_switch_works_on_the_shared_article_editor_too(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    article: SharedArticle = trash.shared_article(
        admin_api.create_shared_article(f"E2E панель ссылки переключение {run_token}")
    )
    admin_page.set_viewport_size(_NARROW)
    admin_page.goto(f"/me/shared/{article.id}/edit")

    body = admin_page.locator("#shared-body")
    preview_pane = admin_page.locator(".editor__pane.editor__preview")
    preview_button = admin_page.get_by_role("button", name=ru("shared.pane_preview"), exact=True)

    expect(body).to_be_visible()
    expect(preview_pane).to_be_hidden()

    preview_button.click()

    expect(preview_pane).to_be_visible()
    expect(preview_pane).to_be_in_viewport()
    expect(body).to_be_hidden()


def test_the_switch_is_a_no_op_at_the_desktop_breakpoint(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """At >=60rem (the default viewport every other editor test already runs
    at) the switch is hidden and both panes stay visible, whichever one the
    class from a narrower session would have picked."""
    post = trash.post(admin_api.create_post(f"E2E панель широкий экран {run_token}"))
    admin_page.goto(f"/blog/{post.slug}/edit")

    switch = admin_page.locator(".editor__pane-switch")
    expect(switch).to_be_hidden()
    expect(admin_page.locator("#post-body")).to_be_visible()
    expect(admin_page.locator(".editor__pane.editor__preview")).to_be_visible()
