"""UI-AUDIT F-011 — the open menu belongs to the capsule it hangs from.

`.nav__capsule` carried no `position`, so on paper the absolutely positioned
`.nav__links` resolved against `.nav`'s padding box — the whole viewport —
while the capsule spans the content box inside it, and the open menu overhung
by one gutter on each side.

On paper. Measuring it says otherwise: `backdrop-filter` on the capsule already
made it a containing block, so the menu was aligned all along in any browser
that supports the property. Removing both declarations reproduces the audit's
overhang exactly (−20 px per side at 360 px); removing only `position: relative`
does not. The declaration is kept so the layout of the one control on every page
does not depend on a visual effect, and this measures the result either way.

Three widths, both themes. A screenshot pair goes to `docs/qa/screenshots/`
because the set kept there is otherwise desktop-only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Browser

from e2e.helpers import ru

pytestmark = pytest.mark.a11y

EDGES = """
() => {
  const capsule = document.querySelector('.nav__capsule');
  const menu = document.getElementById('nav-links');
  const c = capsule.getBoundingClientRect();
  const m = menu.getBoundingClientRect();
  return {
    left: Math.round(m.left - c.left),
    right: Math.round(c.right - m.right),
    border: Math.round(parseFloat(getComputedStyle(capsule).borderLeftWidth)),
    below: Math.round(m.top - c.bottom)
  };
}
"""


@pytest.mark.parametrize("width", [360, 480, 767])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_open_menu_aligns_with_the_capsule(
    browser: Browser, base_url: str, qa_dir: Path, width: int, theme: str
) -> None:
    context = browser.new_context(
        base_url=base_url,
        viewport={"width": width, "height": 720},
        color_scheme=theme,
        reduced_motion="reduce",
    )
    try:
        page = context.new_page()
        page.goto("/")
        page.get_by_role("button", name=ru("nav.menu"), exact=True).click()

        measured = page.evaluate(EDGES)
        if width == 360:
            shots = qa_dir / "screenshots"
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(shots / f"nav-menu-360-{theme}.jpg"),
                clip={"x": 0, "y": 0, "width": width, "height": 320},
                quality=80,
                type="jpeg",
            )
    finally:
        context.close()

    # `inset-inline: 0` resolves against the capsule's *padding* box, so the
    # panel sits exactly one border inside it — 1 px, against the gutter-sized
    # overhang of 20-40 px this replaced.
    assert measured["left"] == measured["border"], measured
    assert measured["right"] == measured["border"], measured
    # The vertical offset was never the problem and is not to be adjusted.
    assert measured["below"] > 0, measured
