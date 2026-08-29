"""UI-AUDIT F-003 — unsaved article text cannot be lost silently (SPEC F50).

Autosave fires 2.5 s after the last keystroke. Closing the tab, or following a
link, inside that window used to lose the text without a word; and when an
autosave *failed*, the only signal was a toast that removed itself after four
seconds, leaving the page looking perfectly normal with unsaved work in it.

Two guards, tested here: the browser's own confirmation while there is anything
unsaved, and a failed state that persists until a save actually succeeds.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from playwright.sync_api import Dialog, Page, expect

from e2e.helpers import AdminApi, Post, SharedArticle, ru

pytestmark = pytest.mark.a11y


@pytest.fixture
def draft(admin_api: AdminApi, trash, run_token: str) -> Post:
    return trash.post(admin_api.create_post(f"E2E защита {run_token}"))


@pytest.fixture
def shared_draft(admin_api: AdminApi, trash, run_token: str) -> SharedArticle:
    return trash.shared_article(admin_api.create_shared_article(f"E2E защита {run_token}"))


@pytest.fixture
def dialogs(admin_page: Page) -> Iterator[list[str]]:
    """Record every dialog and let it through.

    Without a handler Playwright dismisses dialogs, and dismissing a
    `beforeunload` cancels the navigation — so a test that did not listen would
    not merely miss the guard, it would hang against it.
    """
    seen: list[str] = []

    def handle(dialog: Dialog) -> None:
        seen.append(dialog.type)
        dialog.accept()

    admin_page.on("dialog", handle)
    yield seen
    admin_page.remove_listener("dialog", handle)


def _type_without_saving(page: Page, text: str) -> None:
    """Type, then leave immediately — inside the 2.5 s autosave debounce."""
    page.get_by_label(ru("blog.body_label")).fill(text)


def test_leaving_an_editor_with_unsaved_text_asks_first(
    admin_page: Page, draft: Post, dialogs: list[str]
) -> None:
    admin_page.goto(f"/blog/{draft.slug}/edit")
    _type_without_saving(admin_page, "Этот текст ещё не сохранён.")

    admin_page.goto("/blog")

    assert dialogs == ["beforeunload"], dialogs


def test_leaving_a_saved_editor_asks_nothing(
    admin_page: Page, draft: Post, dialogs: list[str]
) -> None:
    admin_page.goto(f"/blog/{draft.slug}/edit")
    _type_without_saving(admin_page, "Этот текст будет сохранён.")

    admin_page.get_by_role("button", name=ru("blog.save"), exact=True).click()
    expect(admin_page.locator("#save-state")).to_contain_text(ru("blog.saved_at", time="").strip())

    admin_page.goto("/blog")

    assert dialogs == [], dialogs


def test_publishing_counts_as_saving(admin_page: Page, draft: Post, dialogs: list[str]) -> None:
    """«Опубликовать» carries `hx-include="#post-form"`, so it writes the text.

    Warning after it would be a false alarm on the one action the owner is most
    likely to finish with.
    """
    admin_page.goto(f"/blog/{draft.slug}/edit")
    _type_without_saving(admin_page, "Этот текст уезжает вместе с публикацией.")

    admin_page.get_by_role("button", name=ru("blog.publish"), exact=True).click()
    expect(admin_page.locator("#editor-meta")).to_contain_text(ru("blog.status_published"))

    admin_page.goto("/blog")

    assert dialogs == [], dialogs


def test_a_failed_save_stays_on_screen(admin_page: Page, draft: Post) -> None:
    """The failed state outlives the toast, and outranks «не сохранено».

    Typing more after a failure does not make the failure untrue, so the region
    must not quietly fall back to the ordinary unsaved wording.
    """
    admin_page.goto(f"/blog/{draft.slug}/edit")
    admin_page.route(f"**/blog/admin/posts/{draft.id}", lambda route: route.abort())

    state = admin_page.locator("#save-state")
    admin_page.get_by_label(ru("blog.body_label")).fill("Сохранение сейчас не пройдёт.")
    admin_page.get_by_role("button", name=ru("blog.save"), exact=True).click()
    expect(state).to_contain_text(ru("blog.save_failed"))

    # Four seconds is how long the toast used to last; the state must outlive it.
    admin_page.wait_for_timeout(4500)
    expect(state).to_contain_text(ru("blog.save_failed"))

    admin_page.get_by_label(ru("blog.body_label")).fill("И ещё немного текста.")
    expect(state).to_contain_text(ru("blog.save_failed"))


def test_a_failed_save_leaves_a_message_that_can_be_read_and_dismissed(
    admin_page: Page, draft: Post
) -> None:
    """UI-AUDIT F-007: the message about lost work outlives four seconds.

    It used to be posted into a `polite` region that removed itself after
    4 000 ms and could not be clicked — so it could not be re-read, and a
    screen reader mid-utterance could miss it entirely. Errors now go to the
    assertive region and stay until the owner closes them.
    """
    admin_page.goto(f"/blog/{draft.slug}/edit")
    # Publishing rather than typing-then-saving: one failed request and exactly
    # one message. A failed *save* also leaves the autosave debounce armed, and
    # a second toast arriving at 2.5 s would make a stale one indistinguishable
    # from a fresh one — the test would pass on the old behaviour.
    admin_page.route(f"**/blog/admin/posts/{draft.id}/publish", lambda route: route.abort())
    admin_page.get_by_role("button", name=ru("blog.publish"), exact=True).click()

    error = admin_page.locator("#toasts-alert .toast--error")
    expect(error).to_have_count(1)
    # A success would interrupt a screen reader if it shared this region.
    expect(admin_page.locator("#toasts-polite .toast--error")).to_have_count(0)

    # Four seconds is how long every toast used to last.
    admin_page.wait_for_timeout(4500)
    expect(error).to_have_count(1)
    expect(error).to_be_visible()

    error.get_by_role("button", name=ru("errors.dismiss")).click()
    expect(error).to_have_count(0)


# --------------------------------------------------------------------------
# The shared-article editor (F70) — the same F50 guarantee, on the structural
# sibling of the blog editor. `editor.js` is one script now, generalised to
# read its target ids off `data-editor-*` on whichever root loaded it
# (REVIEW.md run 10, H-1); these two mirror the blog cases above closely
# enough that the fixtures and assertions can be read side by side.
# --------------------------------------------------------------------------
def test_leaving_a_shared_editor_with_unsaved_text_asks_first(
    admin_page: Page, shared_draft: SharedArticle, dialogs: list[str]
) -> None:
    admin_page.goto(f"/me/shared/{shared_draft.id}/edit")
    admin_page.get_by_label(ru("shared.body_label")).fill("Этот текст ещё не сохранён.")

    admin_page.goto("/me/shared")

    assert dialogs == ["beforeunload"], dialogs


def test_a_failed_shared_save_stays_on_screen(
    admin_page: Page, shared_draft: SharedArticle
) -> None:
    """Mirrors `test_a_failed_save_stays_on_screen`: the failed state outlives
    the toast and outranks «Изменения не сохранены»."""
    admin_page.goto(f"/me/shared/{shared_draft.id}/edit")
    admin_page.route(f"**/me/shared/{shared_draft.id}/save", lambda route: route.abort())

    state = admin_page.locator("#shared-save-state")
    admin_page.get_by_label(ru("shared.body_label")).fill("Сохранение сейчас не пройдёт.")
    admin_page.get_by_role("button", name=ru("shared.save"), exact=True).click()
    expect(state).to_contain_text(ru("shared.save_failed"))

    # Four seconds is how long the toast used to last; the state must outlive it.
    admin_page.wait_for_timeout(4500)
    expect(state).to_contain_text(ru("shared.save_failed"))

    admin_page.get_by_label(ru("shared.body_label")).fill("И ещё немного текста.")
    expect(state).to_contain_text(ru("shared.save_failed"))
