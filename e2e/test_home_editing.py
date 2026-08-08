"""F35 / F46 — the owner edits a copy block in place on the home page.

This flow had no coverage at all, and it was broken: the block's key carries a
dot (`home.intro`), the partial built `id="content-home.intro"`, and htmx read
`#content-home.intro` as «#content-home with class intro». It matched nothing,
htmx logged `htmx:targetError` and no request was ever sent — the button looked
dead. The tests drive the real button, so a regression in the id, the target or
the route all surface here.

There are two such blocks on the page now, which is why every helper takes the
one it is acting on: an unscoped «Править» would match both.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.helpers import ru, token

INTRO = "#content-home-intro"
EYEBROW = "#content-home-eyebrow"


def _open_the_editor(page: Page, block: str) -> None:
    """Click «Править» and wait for htmx to finish settling the swapped form.

    Not `expect(...).to_be_visible()`: htmx shows the form before it settles,
    and a form that has not settled has not had its submit intercepted yet.
    """
    page.evaluate(
        "() => { window.__settled = false;"
        " document.body.addEventListener('htmx:afterSettle',"
        " () => { window.__settled = true; }, { once: true }); }"
    )
    page.locator(block).get_by_role("button", name=ru("editable.edit")).click()
    page.wait_for_function("() => window.__settled === true")


def _save(page: Page, block: str, text: str) -> None:
    page.locator(block).get_by_label(ru("editable.field_label")).fill(text)
    page.locator(block).get_by_role("button", name=ru("editable.save")).click()


def _current_value(page: Page, block: str) -> str:
    return page.locator(block).get_by_label(ru("editable.field_label")).input_value()


def test_the_home_intro_is_edited_in_place_and_the_visitor_sees_it(
    admin_page: Page, page: Page
) -> None:
    written = f"Проверка правки на месте {token()}"

    admin_page.goto("/")
    _open_the_editor(admin_page, INTRO)
    original = _current_value(admin_page, INTRO)

    try:
        _save(admin_page, INTRO, written)

        # Back to the read-only block, carrying the new copy.
        expect(admin_page.locator(f"{INTRO} .editable__value")).to_contain_text(written)
        expect(admin_page.locator("form.editable--editing")).to_have_count(0)

        # And it is the visitor's page that changed, not just the admin's view.
        page.goto("/")
        expect(page.locator(f"{INTRO} .editable__value")).to_contain_text(written)
    finally:
        admin_page.goto("/")
        _open_the_editor(admin_page, INTRO)
        _save(admin_page, INTRO, original)
        expect(admin_page.locator(f"{INTRO} .editable__value")).to_contain_text(
            original.split(".")[0]
        )


def test_the_line_under_the_hero_is_edited_the_same_way(admin_page: Page, page: Page) -> None:
    """F46. It used to be typed into the template, so nobody could change it."""
    written = f"Санкт-Петербург · Python · {token()}"

    admin_page.goto("/")
    _open_the_editor(admin_page, EYEBROW)
    original = _current_value(admin_page, EYEBROW)

    try:
        _save(admin_page, EYEBROW, written)

        expect(admin_page.locator(f"{EYEBROW} .editable__value")).to_contain_text(written)
        # The intro is a separate block and must not have been touched by this.
        expect(admin_page.locator(f"{INTRO} .editable__value")).not_to_contain_text(written)

        page.goto("/")
        expect(page.locator(f"{EYEBROW} .editable__value")).to_contain_text(written)
    finally:
        admin_page.goto("/")
        _open_the_editor(admin_page, EYEBROW)
        _save(admin_page, EYEBROW, original)
        expect(admin_page.locator(f"{EYEBROW} .editable__value")).to_contain_text(original)


def test_cancelling_an_edit_leaves_the_copy_alone(admin_page: Page) -> None:
    admin_page.goto("/")
    before = admin_page.locator(f"{INTRO} .editable__value").inner_text()

    _open_the_editor(admin_page, INTRO)
    admin_page.locator(INTRO).get_by_label(ru("editable.field_label")).fill("выброшенный черновик")
    admin_page.locator(INTRO).get_by_role("button", name=ru("editable.cancel")).click()

    expect(admin_page.locator(f"{INTRO} .editable__value")).to_have_text(before)
