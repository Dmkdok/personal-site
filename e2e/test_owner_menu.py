"""F61 / ADR-027 — the owner's controls live in the capsule, and cover nothing.

The admin bar was fixed at the bottom centre of every signed-in page: it floated
over the end of the document, the document reserved 88 px of clearance for it in
two properties (UI-AUDIT F-015), and «Выйти» — the rarest action the owner takes
— sat permanently under the pointer. All of it is now one button on the
navigation capsule, opening a menu.

That the clearance left nothing behind is measured in `test_a11y.py`. This is
the menu itself: it opens, it closes the three ways it should, and it hands the
caret back — F-002's contract, which a disclosure breaks by leaving the caret
inside the thing it just hid, so the next Tab restarts from the skip link.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, expect

from e2e.helpers import open_owner_menu, ru

FOCUS_IS_ON_THE_BUTTON = """
() => {
  const el = document.activeElement;
  return {
    onButton: el === document.querySelector('[data-owner-menu-toggle]'),
    landedOn: el === document.body ? 'body' : (el.tagName || '').toLowerCase()
  };
}
"""

# The same measurement `test_nav_dropdown.py` makes of the links panel: the open
# menu must belong to the capsule it hangs from, not to the viewport (F-011).
EDGES = """
() => {
  const capsule = document.querySelector('.nav__capsule');
  const panel = document.getElementById('owner-menu');
  const c = capsule.getBoundingClientRect();
  const p = panel.getBoundingClientRect();
  return {
    insideStart: Math.round(p.left - c.left),
    insideEnd: Math.round(c.right - p.right),
    border: Math.round(parseFloat(getComputedStyle(capsule).borderRightWidth)),
    below: Math.round(p.top - c.bottom)
  };
}
"""


def _button(page: Page):
    return page.get_by_role("button", name=ru("auth.owner_menu"), exact=True)


def test_the_menu_opens_on_click_and_closes_on_escape_with_the_caret(admin_page: Page) -> None:
    admin_page.goto("/")
    button = _button(admin_page)
    panel = admin_page.locator("#owner-menu")

    expect(panel).to_be_hidden()
    expect(button).to_have_attribute("aria-expanded", "false")

    button.click()
    expect(panel).to_be_visible()
    expect(button).to_have_attribute("aria-expanded", "true")
    # Everything the bar carried, still reachable — and «Выйти» now takes a
    # second deliberate action rather than sitting under the pointer.
    expect(panel.get_by_role("button", name=ru("auth.mode_view"), exact=True)).to_be_visible()
    expect(panel.get_by_role("button", name=ru("auth.mode_edit"), exact=True)).to_be_visible()
    expect(panel.get_by_role("button", name=ru("auth.logout"), exact=True)).to_be_visible()

    admin_page.keyboard.press("Escape")
    expect(panel).to_be_hidden()
    expect(button).to_have_attribute("aria-expanded", "false")

    caret = admin_page.evaluate(FOCUS_IS_ON_THE_BUTTON)
    assert caret["onButton"], f"Escape dropped the caret on <{caret['landedOn']}>"


def test_a_click_outside_closes_the_menu(admin_page: Page) -> None:
    admin_page.goto("/")
    open_owner_menu(admin_page)

    # Well clear of the capsule, which is fixed at the top of the viewport.
    admin_page.mouse.click(20, 600)
    expect(admin_page.locator("#owner-menu")).to_be_hidden()
    expect(_button(admin_page)).to_have_attribute("aria-expanded", "false")


def test_a_visitor_gets_no_owner_menu(page: Page) -> None:
    """F36, from the other side: the markup is absent, not hidden."""
    page.goto("/")
    expect(_button(page)).to_have_count(0)
    expect(page.locator("#owner-menu")).to_have_count(0)


@pytest.mark.a11y
@pytest.mark.parametrize("width", [360, 1280])
def test_the_open_menu_stays_inside_the_capsule(
    browser: Browser, base_url: str, qa_dir: Path, admin_storage_state: str, width: int
) -> None:
    """F-011 again, for the second dropdown the capsule now carries.

    The links panel overhung its capsule because it resolved against `.nav` —
    the whole viewport — and stayed aligned only by an accident of
    `backdrop-filter`. This one hangs off `.owner-menu`, which says
    `position: relative` in as many words, and is measured at the width where an
    overhang was 20 px per side.
    """
    context = browser.new_context(
        base_url=base_url,
        viewport={"width": width, "height": 780},
        storage_state=admin_storage_state,
    )
    try:
        page = context.new_page()
        page.goto("/")
        open_owner_menu(page)
        measured = page.evaluate(EDGES)
        # The set in `docs/qa/screenshots/` is otherwise anonymous, and this is
        # the one screen of the owner's the iteration is about.
        shots = qa_dir / "screenshots"
        shots.mkdir(parents=True, exist_ok=True)
        page.screenshot(
            path=str(shots / f"owner-menu-{width}.jpg"),
            clip={"x": 0, "y": 0, "width": width, "height": 360},
            quality=80,
            type="jpeg",
        )
    finally:
        context.close()

    # `inset-inline-end: 0` resolves against the capsule's *padding* box, so the
    # panel sits exactly one border inside it — the same 1 px the links panel
    # lands on. The leading edge is wherever the widest item puts it, and only
    # has to be inside as well.
    assert measured["insideEnd"] == measured["border"], measured
    assert measured["insideStart"] >= 0, measured
    assert measured["below"] > 0, measured


def test_the_two_dropdowns_are_never_open_at_once(
    browser: Browser, base_url: str, admin_storage_state: str
) -> None:
    """At 360 px both hang from the same edge of the same capsule.

    The links panel spans the capsule and the owner's menu overlaps its right
    half, so whichever opened second would be read over the first. Opening one
    closes the other; on the desktop, where the links are the row itself rather
    than a dropdown, nothing closes them.
    """
    context = browser.new_context(
        base_url=base_url,
        viewport={"width": 360, "height": 780},
        storage_state=admin_storage_state,
    )
    try:
        page = context.new_page()
        page.goto("/")
        links = page.locator("#nav-links")

        page.get_by_role("button", name=ru("nav.menu"), exact=True).click()
        expect(links).to_be_visible()

        open_owner_menu(page)
        expect(links).to_be_hidden()
        expect(page.get_by_role("button", name=ru("nav.menu"), exact=True)).to_have_attribute(
            "aria-expanded", "false"
        )
    finally:
        context.close()
