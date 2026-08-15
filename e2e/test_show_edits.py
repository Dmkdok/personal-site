"""UI-AUDIT F-018 — every edit affordance can be revealed at once.

Each one appears on hover, which is right for a page that is also the published
page and useless for finding an affordance nobody told you about. «Показать
правки» in the admin bar reveals them all; the choice is remembered the way the
theme is, and the pre-paint script applies it before the first paint so a
reloaded page does not flicker its controls into view.

`aria-pressed` is checked after the toggle *and* after a reload. F-019 was a
control whose pressed state was written once and then drifted; the reload is
where that drift would show.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.helpers import Album, ru

OPACITY = "(el) => getComputedStyle(el).opacity"


def _toggle(page: Page):
    return page.get_by_role("button", name=ru("auth.show_edits"), exact=True)


def test_the_toggle_reveals_the_footer_affordance_and_remembers(admin_page: Page) -> None:
    admin_page.goto("/")

    edit = admin_page.locator(".site-links__edit")
    assert edit.evaluate(OPACITY) == "0", "revealed by default is not the resting state"
    expect(_toggle(admin_page)).to_have_attribute("aria-pressed", "false")

    _toggle(admin_page).click()
    expect(edit).to_have_css("opacity", "1")
    expect(_toggle(admin_page)).to_have_attribute("aria-pressed", "true")

    # Across a page load, and across a different page.
    admin_page.goto("/dev")
    expect(_toggle(admin_page)).to_have_attribute("aria-pressed", "true")
    admin_page.goto("/")
    expect(admin_page.locator(".site-links__edit")).to_have_css("opacity", "1")

    _toggle(admin_page).click()
    expect(admin_page.locator(".site-links__edit")).to_have_css("opacity", "0")
    admin_page.reload()
    expect(_toggle(admin_page)).to_have_attribute("aria-pressed", "false")
    expect(admin_page.locator(".site-links__edit")).to_have_css("opacity", "0")


def test_the_pressed_toggle_looks_pressed(admin_page: Page) -> None:
    """A state announced only to assistive technology is a state most people miss.

    On the top of a long article nothing editable is in the viewport, so the
    press changes an attribute and — before this — not one visible pixel. The
    rule is keyed off `aria-pressed` so the seen state and the announced one
    cannot drift, which is what F-019 was.
    """
    admin_page.goto("/")
    toggle = _toggle(admin_page)

    resting = toggle.evaluate("(el) => getComputedStyle(el).backgroundColor")

    toggle.click()
    expect(toggle).to_have_attribute("aria-pressed", "true")

    # Retried, not sampled: `background-color` is transitioned on `.button`, so
    # reading it in the same tick as the click returns the value it is animating
    # *from* — which is the resting one, and the assertion then fails against
    # correct CSS.
    expect(toggle).not_to_have_css("background-color", resting)
    pressed = toggle.evaluate("(el) => getComputedStyle(el).backgroundColor")
    assert pressed not in ("rgba(0, 0, 0, 0)", "transparent"), pressed

    toggle.click()
    expect(toggle).to_have_attribute("aria-pressed", "false")


def test_the_toggle_reveals_the_photo_tools(admin_page: Page, published_album: Album) -> None:
    admin_page.goto(f"/photo/{published_album.slug}")

    tools = admin_page.locator(".photo-item__admin").first
    assert tools.evaluate(OPACITY) == "0"

    _toggle(admin_page).click()
    expect(tools).to_have_css("opacity", "1")
    # The scrim itself stays click-through so the photograph still opens.
    assert tools.evaluate("(el) => getComputedStyle(el).pointerEvents") == "none"
    assert (
        tools.locator(".photo-item__tools").evaluate("(el) => getComputedStyle(el).pointerEvents")
        == "auto"
    )

    _toggle(admin_page).click()


def test_a_visitor_gets_neither_the_toggle_nor_its_script(page: Page) -> None:
    page.goto("/")

    expect(page.get_by_role("button", name=ru("auth.show_edits"), exact=True)).to_have_count(0)
    assert "edits.js" not in page.content()
