"""ADR-028 — the owner's affordances are a mode, not a reveal on top of hover.

Before I4 there were two discovery mechanisms for the same controls running at
once: every affordance rested at `opacity: 0` and appeared on hover, and
«Показать правки» forced them all visible. The toggle closed UI-AUDIT F-018
without removing its cause, so it duplicated hover instead of replacing it.

Now there are two named modes and one mechanism. In **«Просмотр»** no edit
control is on the page at all — not transparent, *absent*, which is why the
checks below count roles and measure boxes rather than reading `opacity`; the
page the owner reads is the page a visitor reads. In **«Правка»** all three
affordance families are visible with the pointer nowhere near them.

The choice is remembered the way the theme is, and the pre-paint script applies
it before the first paint so a reloaded page does not flicker.

`aria-pressed` is checked after the switch *and* after a reload. F-019 was a
control whose pressed state was written once and then drifted; the reload is
where that drift would show.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.helpers import EDITING, Album, open_owner_menu, ru, switch_mode

#: A box on the page, or none at all. `display: none` is what «Просмотр» uses,
#: so an element in the document with no rects is exactly what it should leave.
RENDERED = "(el) => el.getClientRects().length > 0"

BACKGROUND = "(el) => getComputedStyle(el).backgroundColor"


def _option(page: Page, mode: str):
    """One half of the switch, in the owner's menu since ADR-027."""
    key = "auth.mode_edit" if mode == "edit" else "auth.mode_view"
    return open_owner_menu(page).get_by_role("button", name=ru(key), exact=True)


def test_view_mode_carries_no_edit_control_at_all(admin_page: Page, published_album: Album) -> None:
    """The whole point of the change: absent, not transparent.

    A control at `opacity: 0` is still in the accessibility tree, still a tab
    stop and still under the pointer — which is why hover was a discovery
    mechanism in the first place. `get_by_role` does not match an element the
    page has removed from the tree, so a count of zero here is the assertion
    that hover-reveal cannot pass.
    """
    admin_page.goto("/")
    assert admin_page.evaluate(EDITING) is False, "«Просмотр» is not the resting mode"

    expect(admin_page.get_by_role("button", name=ru("footer.edit"), exact=True)).to_have_count(0)
    expect(admin_page.get_by_role("button", name=ru("editable.edit"), exact=True)).to_have_count(0)

    # The markup is in the document — this is the owner's page. What «Просмотр»
    # takes away is the box, and with it the tab stop and the hover target.
    footer_edit = admin_page.locator(".site-links__edit")
    assert footer_edit.count() >= 1, "the owner's footer carries no edit control at all"
    assert footer_edit.first.evaluate(RENDERED) is False

    admin_page.goto(f"/photo/{published_album.slug}")
    expect(admin_page.get_by_role("group", name=ru("photo.photo_actions_label"))).to_have_count(0)
    assert admin_page.locator(".photo-item__admin").first.evaluate(RENDERED) is False


def test_edit_mode_shows_every_affordance_and_remembers(
    admin_page: Page, published_album: Album
) -> None:
    """All three families at once, with the pointer nowhere near the page."""
    admin_page.goto("/")
    switch_mode(admin_page, "edit")

    expect(admin_page.get_by_role("button", name=ru("footer.edit"), exact=True)).to_be_visible()
    expect(admin_page.locator(".editable__edit").first).to_be_visible()
    expect(_option(admin_page, "edit")).to_have_attribute("aria-pressed", "true")
    expect(_option(admin_page, "view")).to_have_attribute("aria-pressed", "false")

    # Across a page load, and across a different page.
    admin_page.goto("/dev")
    assert admin_page.evaluate(EDITING) is True
    expect(_option(admin_page, "edit")).to_have_attribute("aria-pressed", "true")

    admin_page.goto(f"/photo/{published_album.slug}")
    tools = admin_page.locator(".photo-item__admin").first
    expect(tools).to_be_visible()
    # The scrim stays click-through so the photograph still opens; its children
    # take their pointer events back, as they did on hover.
    assert tools.evaluate("(el) => getComputedStyle(el).pointerEvents") == "none"
    assert (
        tools.locator(".photo-item__tools").evaluate("(el) => getComputedStyle(el).pointerEvents")
        == "auto"
    )

    switch_mode(admin_page, "view")
    expect(admin_page.locator(".photo-item__admin").first).to_be_hidden()
    admin_page.reload()
    assert admin_page.evaluate(EDITING) is False
    expect(_option(admin_page, "view")).to_have_attribute("aria-pressed", "true")


def test_the_editable_region_is_outlined_only_in_edit_mode(admin_page: Page) -> None:
    """ADR-028: «Правка» marks the regions, not only the buttons.

    Without it the mode announces itself in an attribute and, at the top of a
    long page where nothing editable is in view, in not one visible pixel —
    which is the shape F-019 had.
    """
    admin_page.goto("/")
    region = admin_page.locator(".editable").first

    assert region.evaluate("(el) => getComputedStyle(el).outlineStyle") == "none"

    switch_mode(admin_page, "edit")
    expect(region).to_have_css("outline-style", "dashed")

    # The chosen half of the switch looks chosen, too — a state announced only
    # to assistive technology is a state most people miss.
    chosen = _option(admin_page, "edit")
    other = _option(admin_page, "view")
    expect(chosen).not_to_have_css("background-color", other.evaluate(BACKGROUND))


def test_a_visitor_gets_neither_the_switch_nor_its_script(page: Page) -> None:
    page.goto("/")

    expect(page.get_by_role("button", name=ru("auth.mode_edit"), exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name=ru("auth.mode_view"), exact=True)).to_have_count(0)
    assert "edits.js" not in page.content()
