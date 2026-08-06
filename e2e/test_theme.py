"""Launch flow 5 — theme persistence (SPEC F11; user flow 6)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Browser, Page, expect

from e2e.helpers import ru, theme_of

THEME_BUTTON = ru("nav.theme_label")

# Recorded before any page script runs. `data-theme` has to be on <html> while
# the document is still parsing, or the visitor sees a flash of the wrong theme.
WATCH_FIRST_PAINT = """
window.__themeApplied = null;
// Observed on `document` with subtree: at init-script time <html> may not have
// been created yet, and observing a null node throws the watcher away silently.
new MutationObserver(function (records) {
  for (var i = 0; i < records.length; i += 1) {
    if (records[i].attributeName === 'data-theme' && window.__themeApplied === null) {
      window.__themeApplied = {
        readyState: document.readyState,
        bodyChildren: document.body ? document.body.childElementCount : -1,
        value: document.documentElement.dataset.theme || null
      };
    }
  }
}).observe(document, {
  attributes: true,
  subtree: true,
  attributeFilter: ['data-theme']
});
"""


@pytest.mark.launch_flow
def test_theme_choice_persists_and_is_applied_before_first_paint(
    browser: Browser, base_url: str
) -> None:
    # A first visit follows the OS preference: the site sets nothing itself.
    context = browser.new_context(base_url=base_url, color_scheme="light")
    try:
        page = context.new_page()
        page.goto("/")
        assert theme_of(page) is None, "an untouched first visit must not pin a theme"

        toggle = page.get_by_role("button", name=THEME_BUTTON)
        expect(toggle).to_have_attribute("aria-pressed", "false")

        # Keyboard, not a click: the toggle is on the launch checklist's
        # keyboard pass as well.
        toggle.focus()
        page.keyboard.press("Enter")
        expect(toggle).to_have_attribute("aria-pressed", "true")
        assert theme_of(page) == "dark"
        assert page.evaluate("() => localStorage.getItem('theme')") == "dark"

        # Survives a reload…
        page.reload()
        assert theme_of(page) == "dark"
        expect(page.get_by_role("button", name=THEME_BUTTON)).to_have_attribute(
            "aria-pressed", "true"
        )

        # …a navigation to another section…
        page.get_by_role("link", name=ru("nav.blog"), exact=True).click()
        assert theme_of(page) == "dark"

        # …and a brand new tab in the same profile (F11: "on subsequent visits").
        second = context.new_page()
        second.add_init_script(WATCH_FIRST_PAINT)
        second.goto("/photo")
        assert theme_of(second) == "dark"

        applied = second.evaluate("() => window.__themeApplied")
        assert applied is not None, "the pre-paint script never set data-theme"
        assert applied["value"] == "dark"
        # No flash: the attribute was on <html> before <body> had any content.
        assert applied["readyState"] == "loading", applied
        assert applied["bodyChildren"] <= 0, applied

        # Toggling back is symmetric.
        page.bring_to_front()
        page.get_by_role("button", name=THEME_BUTTON).click()
        assert theme_of(page) == "light"
        page.reload()
        assert theme_of(page) == "light"
    finally:
        context.close()


def test_the_dark_theme_is_dark_grey_and_never_pure_black(page: Page) -> None:
    """F11 spells this out; a pure-black canvas was ruled out in the brief."""
    page.goto("/")
    page.evaluate("() => localStorage.setItem('theme', 'dark')")
    page.reload()

    background = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
    channels = [int(part) for part in background.strip("rgba()").split(",")[:3]]
    assert channels != [0, 0, 0], background
    assert max(channels) >= 8, f"background {background} is indistinguishable from black"
