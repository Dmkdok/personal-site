"""I5 exit criterion 4 — in «Просмотр» the owner's page *is* the visitor's page.

I4 gave the owner two named modes but gated three selector families with them.
Everywhere else the owner's page stayed the owner's page: the upload zone, the
album action row, both reorder hints, the draft chips, the unpublished cards and
every tile still in the pipeline were all on the page in both modes. F55 said
otherwise, so this is a defect against a requirement already written and not a
new one (ADR-032).

What is measured here is **rendered boxes**, never computed `opacity` and never
a count of DOM nodes. «Просмотр» leaves every owner-only node in the document
and takes away its box, so laid-out-or-not is the only measure that tells the
two modes apart — and it is also the measure that matters, because a box is what
a pointer can hit, what a screen reader walks and what a tab stop needs.

Two exclusions, both deliberate, both recorded in ADR-032:

* **the owner's menu**, which is the mode switch itself — a mode that hides the
  way out of itself cannot be left;
* **`photo-item--undescribed`**, a modifier on a tile that stays either way. The
  class is server-emitted for the owner and paints nothing in «Просмотр», so it
  changes a class list without changing a box; it is filtered out of the
  signature rather than out of the page.

One caveat worth knowing before reading a failure: `/photo` is bounded for a
visitor and whole for the owner (ADR-022), so above `PAGE_SIZE` published albums
the two sides genuinely hold different content and the diff below would report
album cards. That is the decision showing through, not a leak — the assertion
message says so.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from e2e.helpers import Album, switch_mode

#: Both sides at one size. Nothing here depends on the viewport, but the nav
#: swaps its links for a toggle at 768 px, so two contexts measured at two widths
#: would differ by that swap and by nothing that is under test.
VIEWPORT = {"width": 1280, "height": 900}

EXCLUDED = [".owner-menu"]

BOX_SIGNATURES = """
(excluded) => {
  const roots = excluded.flatMap((selector) => [...document.querySelectorAll(selector)]);
  const counts = {};
  for (const el of document.body.querySelectorAll('*')) {
    if (roots.some((root) => root.contains(el))) continue;
    if (!el.getClientRects().length) continue;
    const classes = [...el.classList]
      .filter((name) => name !== 'photo-item--undescribed')
      .sort();
    const key = el.tagName.toLowerCase() + classes.map((name) => '.' + name).join('');
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}
"""


def _boxes(page: Page, path: str) -> dict[str, int]:
    page.goto(path)
    return page.evaluate(BOX_SIGNATURES, EXCLUDED)


def _diff(owner: dict[str, int], visitor: dict[str, int]) -> list[str]:
    """Every signature the two pages disagree about, owner's count first."""
    lines = []
    for key in sorted(set(owner) | set(visitor)):
        mine, theirs = owner.get(key, 0), visitor.get(key, 0)
        if mine != theirs:
            lines.append(f"  {key}: owner {mine}, visitor {theirs}")
    return lines


def test_view_mode_renders_exactly_the_visitors_page(
    admin_page: Page, page: Page, published_album: Album
) -> None:
    """Five pages, the same content, two sessions, the same set of boxes.

    Fails today on the album alone by the upload zone, the action row, two hints
    and the scrim over every tile — which is the whole of what T135 removes.
    """
    admin_page.set_viewport_size(VIEWPORT)
    page.set_viewport_size(VIEWPORT)

    admin_page.goto("/")
    switch_mode(admin_page, "view")

    for path in ("/", "/blog", "/photo", f"/photo/{published_album.slug}", "/dev"):
        owner = _boxes(admin_page, path)
        # Guards the guard: a page whose owner-only blocks were never emitted
        # would agree with the visitor's for the wrong reason. Every page carries
        # at least the footer's edit control.
        marked = admin_page.locator(".owner-only").count()
        assert marked, f"{path} carries no owner-only block at all — is this the owner's page?"

        visitor = _boxes(page, path)
        differences = _diff(owner, visitor)
        assert not differences, (
            f"«Просмотр» on {path} is not the page a visitor reads "
            f"({marked} owner-only blocks in the document):\n" + "\n".join(differences) + "\n"
            "If the lines above are album cards, check whether there are now more "
            "than PAGE_SIZE published albums: the owner's index is unbounded by "
            "ADR-022, so past that the two sides hold different content."
        )


@pytest.mark.parametrize(
    "path,selector",
    [
        ("album", "#upload-zone"),
        ("album", ".photo-item__admin"),
        ("/photo", ".photo-actions"),
        ("/dev", ".board-actions"),
    ],
)
def test_named_owner_surfaces_have_no_box_in_view_mode(
    admin_page: Page, published_album: Album, path: str, selector: str
) -> None:
    """The four the impact map named, by name, so a failure says which one.

    The parity check above would catch each of these, but it reports a signature
    diff; these say «the upload zone is on the page in «Просмотр»» in as many
    words. The element must be *in the document* — this is the owner's page, and
    a count of zero here would mean the template stopped emitting it at all.
    """
    admin_page.set_viewport_size(VIEWPORT)
    admin_page.goto("/")
    switch_mode(admin_page, "view")
    admin_page.goto(f"/photo/{published_album.slug}" if path == "album" else path)

    element = admin_page.locator(selector).first
    assert element.count() >= 1, f"{selector} is not in the owner's document at all"
    assert element.evaluate("(el) => el.getClientRects().length") == 0, (
        f"{selector} still has a box in «Просмотр»"
    )
