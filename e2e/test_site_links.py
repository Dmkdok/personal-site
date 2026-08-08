"""T084 — the owner changes an outbound link from the site itself.

The four social links and the copyright name used to be typed into two
templates. They are `site_content` rows now, rendered twice: as the footer list
and as the home page's chips. Both assertions below are deliberate — a save
that reaches one rendering and not the other is precisely the bug this replaced.

Driving the real affordance also guards the dot-in-an-id trap: the keys carry a
dot (`footer.github`), and an id built from one unescaped would make htmx read
`#site-link-footer.github` as a class selector, log `htmx:targetError` and do
nothing at all. See `partials/editable.html`.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.helpers import ru, token

BLOCK = "#site-links"
CONTACTS = "#site-contacts"


def _open_the_editor(page: Page) -> None:
    """Click the footer's edit button and wait for htmx to settle the form.

    Not `expect(...).to_be_visible()`: htmx shows the swapped form before it
    settles, and a form that has not settled has not had its submit intercepted
    yet. Filling and submitting without this wait flakes about one run in three.
    """
    page.evaluate(
        "() => { window.__settled = false;"
        " document.body.addEventListener('htmx:afterSettle',"
        " () => { window.__settled = true; }, { once: true }); }"
    )
    page.get_by_role("button", name=ru("footer.edit"), exact=True).click()
    page.wait_for_function("() => window.__settled === true")


def _field(page: Page, slug: str):
    return page.get_by_label(ru(f"footer.{slug}_label"), exact=True)


def _save(page: Page) -> None:
    page.get_by_role("button", name=ru("editable.save"), exact=True).click()


def test_the_owner_changes_a_link_and_a_visitor_sees_it(admin_page: Page, page: Page) -> None:
    changed = f"https://t.me/{token()}"

    admin_page.goto("/")
    _open_the_editor(admin_page)
    original = _field(admin_page, "telegram").input_value()

    try:
        _field(admin_page, "telegram").fill(changed)
        _save(admin_page)

        # The footer swapped back to the rendered block, carrying the new
        # address, and the home page's chips came with it out of band — one
        # save, both renderings, no reload.
        expect(admin_page.locator(f'{BLOCK} a[href="{changed}"]')).to_be_visible()
        expect(admin_page.locator(f'{CONTACTS} a[href="{changed}"]')).to_be_visible()
        expect(admin_page.locator("form#site-links")).to_have_count(0)

        # And it is the visitor's page that changed, not just the owner's view.
        page.goto("/")
        expect(page.locator(f'{BLOCK} a[href="{changed}"]')).to_be_visible()
        expect(page.locator(f'{CONTACTS} a[href="{changed}"]')).to_be_visible()
        expect(page.locator(".site-links__edit")).to_have_count(0)
    finally:
        admin_page.goto("/")
        _open_the_editor(admin_page)
        _field(admin_page, "telegram").fill(original)
        _save(admin_page)
        expect(admin_page.locator(f'{BLOCK} a[href="{original}"]')).to_be_visible()


def test_a_javascript_url_is_refused_and_the_stored_link_survives(admin_page: Page) -> None:
    admin_page.goto("/")
    _open_the_editor(admin_page)
    original = _field(admin_page, "vk").input_value()

    _field(admin_page, "vk").fill("javascript:alert(1)")
    _save(admin_page)

    # The form comes back with the error beside the field, and what was typed
    # is still there to be corrected rather than retyped (F37).
    expect(admin_page.locator(".site-links__error")).to_have_text(ru("footer.invalid_url"))
    expect(_field(admin_page, "vk")).to_have_value("javascript:alert(1)")

    # Nothing was written: a reload still shows the address that was there, and
    # no scheme outside http(s) ever reaches an href.
    admin_page.goto("/")
    expect(admin_page.locator(f'{BLOCK} a[href="{original}"]')).to_be_visible()
    expect(admin_page.locator('a[href^="javascript:"]')).to_have_count(0)


def test_the_owner_edits_the_whole_copyright_line(admin_page: Page, page: Page) -> None:
    """F45 — symbol, year and name are one editable value (ADR-015).

    The template used to print `© {{ current_year }} {{ rights }}`, so the year
    advanced by itself and could not be changed; the assertion that matters is
    that what the owner typed is what the visitor reads, character for character.
    """
    line = f"© 2019—2026 Дмитрий Богданов · {token()}"

    admin_page.goto("/")
    _open_the_editor(admin_page)
    field = admin_page.get_by_label(ru("footer.rights_label"), exact=True)
    original = field.input_value()

    try:
        field.fill(line)
        _save(admin_page)

        expect(admin_page.locator(f"{BLOCK} .site-links__rights")).to_have_text(line)

        page.goto("/")
        expect(page.locator(f"{BLOCK} .site-links__rights")).to_have_text(line)
    finally:
        admin_page.goto("/")
        _open_the_editor(admin_page)
        admin_page.get_by_label(ru("footer.rights_label"), exact=True).fill(original)
        _save(admin_page)
        expect(admin_page.locator(f"{BLOCK} .site-links__rights")).to_have_text(original)
