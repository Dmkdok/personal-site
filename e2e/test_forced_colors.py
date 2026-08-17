"""UI-AUDIT F-013 — hover, focus and «you are here» survive a contrast theme.

Forced colours discard `box-shadow` and repaint every background with the
system's own. Three of this site's states were expressed in exactly those two
properties: the warm rim that is the whole hover and focus language of the
contact sheet, the accent pill that marks the current section, and the tint
under a home-page entry. All three vanished, and the contact sheet's tiles were
left with no focus indicator at all — the global ring cannot stand in, because
`photo.css` pulls it 2 px inside expecting the rim to carry the weight.

Chromium's `forced_colors` emulation is not a Windows contrast theme: it applies
the media query and the forced colour adjustments, not a specific palette. It is
enough to prove that a property which survives is doing the work, which is what
the finding is about. The Edge pass on a real theme is recorded separately in
`docs/qa/forced-colors.md`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from playwright.sync_api import Browser

from e2e.helpers import Album, ru

pytestmark = pytest.mark.a11y

READ_STATE = """
(el) => {
  const s = getComputedStyle(el);
  return {
    outlineStyle: s.outlineStyle,
    outlineWidth: s.outlineWidth,
    borderStyle: s.borderTopStyle,
    borderWidth: s.borderTopWidth,
    decoration: s.textDecorationLine
  };
}
"""


@pytest.fixture
def forced_colors_page(browser: Browser, base_url: str):
    context = browser.new_context(
        base_url=base_url, forced_colors="active", reduced_motion="reduce"
    )
    page = context.new_page()
    yield page
    context.close()


def _width(value: str) -> float:
    return float(value.removesuffix("px"))


def test_a_thumbnail_still_shows_hover_and_focus(
    forced_colors_page, published_album: Album, qa_dir: Path
) -> None:
    page = forced_colors_page
    page.goto(f"/photo/{published_album.slug}")

    tile = page.locator(".photo-item__link").first
    tile.hover()
    hovered = tile.evaluate(READ_STATE)
    tile.focus()
    focused = tile.evaluate(READ_STATE)

    shots = qa_dir / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shots / "forced-colors-photo.jpg"), quality=80, type="jpeg")

    assert hovered["outlineStyle"] == "solid", hovered
    assert _width(hovered["outlineWidth"]) >= 2, hovered
    assert focused["outlineStyle"] == "solid", focused
    assert _width(focused["outlineWidth"]) >= 2, focused


def test_the_current_section_is_still_marked(forced_colors_page, qa_dir: Path) -> None:
    page = forced_colors_page
    page.goto("/blog")

    current = page.get_by_role("link", name=ru("nav.blog"), exact=True)
    marked = current.evaluate(READ_STATE)
    other = page.get_by_role("link", name=ru("nav.photo"), exact=True)
    plain = other.evaluate(READ_STATE)

    assert marked["borderStyle"] == "solid", marked
    assert _width(marked["borderWidth"]) >= 2, marked
    # And the distinction is a distinction: the other three carry no border.
    assert plain["borderStyle"] != "solid" or _width(plain["borderWidth"]) == 0, plain

    (qa_dir / "forced-colors.json").write_text(
        json.dumps(
            {
                "recorded": datetime.now(UTC).strftime("%Y-%m-%d"),
                "engine": "chromium, Playwright forced_colors=active",
                "note": "emulation, not a Windows contrast theme; see docs/qa/forced-colors.md",
                "current_section": marked,
                "other_section": plain,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_the_video_facade_keeps_its_plates(forced_colors_page, published_video_post) -> None:
    """T138: the glyph's disc and the label's plate are backgrounds, and forced
    colours repaint every one of them with the system's own.

    Over a poster that would leave both floating on the picture with nothing
    behind them, so `prose.css` gives each a border under `forced-colors` — the
    same treatment the current navigation link already has (UI-AUDIT F-013).
    """
    page = forced_colors_page
    page.goto(f"/blog/{published_video_post.slug}")

    for selector in (".prose-video__glyph", ".prose-video__label"):
        state = page.locator(selector).evaluate(READ_STATE)
        assert state["borderStyle"] == "solid", (selector, state)
        assert _width(state["borderWidth"]) >= 1, (selector, state)


def test_a_home_entry_still_answers_the_pointer(forced_colors_page) -> None:
    page = forced_colors_page
    page.goto("/")

    entry = page.locator(".entry").first
    entry.hover()
    hovered = entry.evaluate(READ_STATE)

    assert hovered["outlineStyle"] == "solid", hovered
    assert _width(hovered["outlineWidth"]) >= 2, hovered
