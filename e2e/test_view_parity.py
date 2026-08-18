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

from e2e.conftest import Trash
from e2e.helpers import AdminApi, Album, switch_mode

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
        ("/dev", "[data-drag-handle]"),
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


# --------------------------------------------------------------- drag-reorder
#: SortableJS starts on the first move after a press and wants a few of them; one
#: jump from source to target is read as a click and drops nothing.
DRAG_STEPS = 8

#: Where a completed drop reports itself.
ORDER_ENDPOINT = "/dev/admin/order"

#: How long a drop that *did* happen is given to post itself. Only the negative
#: check waits on the clock — it has nothing to wait for — and a window this wide
#: is several times what the drop takes on this host.
SETTLE_MS = 1500


def _order(page: Page) -> list[str]:
    return page.eval_on_selector_all(
        "#project-list [data-project-id]", "(nodes) => nodes.map((n) => n.dataset.projectId)"
    )


def _drag(page: Page, source: object, target: object) -> None:
    """Press on `source`, walk the pointer onto `target`, release.

    Both are scrolled into view first: `bounding_box()` is viewport-relative, and
    a board long enough to put the cards below the fold hands back coordinates
    the mouse cannot reach — the drag then silently does nothing and the test
    passes for the wrong reason.
    """
    target.scroll_into_view_if_needed()
    source.scroll_into_view_if_needed()
    start = source.bounding_box()
    end = target.bounding_box()
    assert start and end, "nothing to drag from or onto"
    height = page.viewport_size["height"]
    assert start["y"] >= 0 and end["y"] + end["height"] <= height, (
        f"the two cards do not fit the viewport together: {start}, {end}"
    )
    from_x, from_y = start["x"] + start["width"] / 2, start["y"] + start["height"] / 2
    to_x, to_y = end["x"] + end["width"] / 2, end["y"] + end["height"] / 2

    page.mouse.move(from_x, from_y)
    page.mouse.down()
    # Sortable arms the drag on the first move after the press; a single jump to
    # the target reads as a click.
    page.mouse.move(from_x, from_y + 6)
    for step in range(1, DRAG_STEPS + 1):
        page.mouse.move(
            from_x + (to_x - from_x) * step / DRAG_STEPS,
            from_y + (to_y - from_y) * step / DRAG_STEPS,
        )
    page.mouse.up()


@pytest.fixture
def two_projects(admin_api: AdminApi, trash: Trash, run_token: str) -> list[str]:
    """Two published projects at the end of the board, in creation order.

    Published, because an unpublished project's whole row is `owner-only` since
    T135 — a draft has no card in «Просмотр» to drag at all, and the defect this
    covers is about the cards a visitor can see.
    """
    first = trash.project_id(admin_api.create_project(f"E2E порядок A {run_token}"))
    second = trash.project_id(admin_api.create_project(f"E2E порядок B {run_token}"))
    admin_api.publish_project(first)
    admin_api.publish_project(second)
    return [str(first), str(second)]


def test_view_mode_cannot_drag_the_project_board(admin_page: Page, two_projects: list[str]) -> None:
    """The defect run 7 found: in «Просмотр» /dev could still be reordered.

    The handle used to be `.project__body` — the card's own text, laid out in
    both modes and carrying no marker — so the owner reading the visitor's page
    could drag a project by its summary and silently POST a new public order.
    Exit criterion 4 could not see it: a drag target is not a box of its own.

    Two independent assertions, because either alone can pass for the wrong
    reason. The request one is the sharp one — `onEnd` fires on drop and htmx
    issues the POST at once, so a drop that happened is a request that exists.
    The order is then read back from a reload, so what it reports is the
    server's and not the DOM's.
    """
    admin_page.goto("/")
    switch_mode(admin_page, "view")
    admin_page.goto("/dev")

    before = _order(admin_page)
    assert before[-2:] == two_projects, f"the fixture is not at the end of the board: {before[-3:]}"

    orders: list[str] = []
    admin_page.on(
        "request", lambda r: orders.append(r.url) if r.url.endswith(ORDER_ENDPOINT) else None
    )

    first, second = (admin_page.locator(f"#project-{pid} .project__body") for pid in two_projects)
    _drag(admin_page, first, second)
    admin_page.wait_for_timeout(SETTLE_MS)

    assert not orders, f"«Просмотр» posted a new order for the project board: {orders}"
    admin_page.reload()
    assert _order(admin_page) == before, (
        "«Просмотр» let the project board be dragged — the order a visitor reads changed"
    )


def test_edit_mode_still_drags_the_project_board(admin_page: Page, two_projects: list[str]) -> None:
    """And the handle inside the marker still does the job it was moved for.

    Without this, the fix above would be indistinguishable from breaking drag
    ordering altogether — the ↑/↓ buttons would still pass every other test.
    """
    admin_page.goto("/")
    switch_mode(admin_page, "edit")
    admin_page.goto("/dev")

    before = _order(admin_page)
    assert before[-2:] == two_projects, f"the fixture is not at the end of the board: {before[-3:]}"

    first, second = (
        admin_page.locator(f"#project-{pid} [data-drag-handle]") for pid in two_projects
    )
    # Waiting on the response and not on the DOM: Sortable moves the node the
    # moment it is dropped, so the list reads as reordered before the server has
    # been told, and a reload started there aborts the POST.
    with admin_page.expect_response(lambda r: r.url.endswith(ORDER_ENDPOINT) and r.status == 200):
        _drag(admin_page, first, second)

    admin_page.reload()
    assert _order(admin_page) == before[:-2] + list(reversed(two_projects)), (
        "the drag handle in «Правка» did not reorder the board"
    )
