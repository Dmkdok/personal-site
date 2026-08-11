"""Launch flow 6 — site-wide search (SPEC F10; user flow 5)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, ru

SEARCH_FIELD = ru("nav.search_label")

# The wrapping label and the input both react to focus, so the two have to be
# read together to tell one ring from two — and where the one ring is painted.
MEASURE_SEARCH_FOCUS = """
() => {
  const label = document.querySelector('.search-field');
  const input = document.querySelector('.search-field__input');

  const ring = (node) => {
    const s = getComputedStyle(node);
    const off = parseFloat(s.outlineOffset) || 0;
    const width = s.outlineStyle === 'none' ? 0 : parseFloat(s.outlineWidth);
    return {
      width,
      color: s.outlineColor,
      border: s.borderColor,
      // A negative offset pulls the stroke inside the box it belongs to; this
      // is how far in its innermost painted pixel reaches.
      inset: width ? Math.max(0, -off) : 0,
    };
  };
  const box = (node) => {
    const r = node.getBoundingClientRect();
    return [Math.round(r.left), Math.round(r.right), Math.round(r.width), Math.round(r.height)];
  };

  // Resolve the tokens through a throwaway element: `--accent` is a
  // `light-dark()` pair as authored and only becomes a colour once used.
  const probe = document.createElement('span');
  document.body.appendChild(probe);
  const resolve = (token) => {
    probe.style.color = `var(${token})`;
    return getComputedStyle(probe).color;
  };
  const accents = [resolve('--accent'), resolve('--accent-ink')];
  probe.remove();

  return {
    label: ring(label),
    input: ring(input),
    labelBox: box(label),
    inputBox: box(input),
    accents,
  };
}
"""


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_focused_search_field_shows_exactly_one_ring(page: Page, theme: str) -> None:
    """One ring, round the whole field, clear of the text inside it.

    The field is one control to the eye — icon, text and clear button in a
    single capsule — but the ring used to be painted on the inner `<input>`,
    pulled 3px in by `outline-offset` against 2px of padding. So it read as a
    second, tighter ring inside the field's own border, and its left stroke
    landed on top of the first letter of the query.

    The three assertions are one contract: the ring exists, it is on the field,
    and it stays out of the box the text lives in.
    """
    page.goto("/")
    page.evaluate("(t) => localStorage.setItem('theme', t)", theme)
    page.goto("/")

    resting = page.evaluate(MEASURE_SEARCH_FOCUS)
    assert resting["label"]["width"] == 0, resting

    page.get_by_role("searchbox", name=SEARCH_FIELD).focus()
    # The ring is an outline and appears at once; `border-color` underneath it
    # is transitioned (`--dur-fast`, 130ms). Waiting it out costs nothing and
    # means a failure prints the colours the eye actually sees, not the
    # resting ones caught mid-fade.
    page.wait_for_timeout(300)
    measured = page.evaluate(MEASURE_SEARCH_FOCUS)

    # The indicator itself survives — this must never be "fixed" by removing it.
    assert measured["label"]["width"] >= 2, measured
    assert measured["label"]["color"] in measured["accents"], measured

    # …and the input inside it draws nothing, so there is exactly one ring.
    assert measured["input"]["width"] == 0, measured

    # The stroke never reaches the text: it stops outside the input's own box.
    inset = measured["label"]["inset"]
    assert measured["inputBox"][0] - measured["labelBox"][0] >= inset, measured
    assert measured["labelBox"][1] - measured["inputBox"][1] >= inset, measured

    # Focus paints; it does not move the field inside the nav capsule.
    assert measured["labelBox"][2:] == resting["labelBox"][2:], (measured, resting)


def test_the_search_fields_clear_button_still_clears_it(page: Page) -> None:
    """`appearance: none` repaints the browser's clear button — it must still work.

    The glyph is ours now (a mask over `--text-faint`, so it follows the tokens
    and both themes instead of arriving white on one and blue on the other), but
    the behaviour behind it is still the user agent's, and dropping the native
    appearance is exactly the kind of change that can take the behaviour with it.
    """
    page.goto("/")
    field = page.get_by_role("searchbox", name=SEARCH_FIELD)
    field.fill("Пример")
    expect(field).to_have_value("Пример")

    box = field.bounding_box()
    assert box, "the search field is not laid out"
    # The clear button sits at the trailing edge of the input's own box.
    page.mouse.click(box["x"] + box["width"] - 10, box["y"] + box["height"] / 2)

    expect(field).to_have_value("")


@pytest.mark.launch_flow
def test_search_from_the_pill_groups_matches_by_content_type(
    page: Page, base_url: str, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """The test creates everything it looks for; it never searches for
    content another test happened to leave behind."""
    album_title = f"E2E альбом {run_token}"
    post_title = f"E2E статья {run_token}"

    album = trash.album(admin_api.create_album(album_title, "Подпись для поиска"))
    admin_api.publish_album(album)
    post = trash.post(admin_api.create_post(post_title))
    admin_api.publish_post(post, body_md=f"Текст статьи со словом {run_token}.")

    # Typed into the pill and submitted with Enter — no mouse.
    page.goto("/")
    field = page.get_by_role("searchbox", name=SEARCH_FIELD)
    field.focus()
    expect(field).to_be_focused()
    page.keyboard.type(run_token)
    page.keyboard.press("Enter")

    expect(page).to_have_url(f"{base_url}/search?q={run_token}")
    expect(page.get_by_role("heading", level=1)).to_contain_text(run_token)

    # F10: grouped under labelled headings, one group per content type.
    expect(page.get_by_role("heading", name=ru("search.group_posts"))).to_be_visible()
    expect(page.get_by_role("heading", name=ru("search.group_albums"))).to_be_visible()
    expect(page.get_by_role("link", name=post_title)).to_be_visible()
    expect(page.get_by_role("link", name=album_title)).to_be_visible()

    # The result actually goes somewhere.
    page.get_by_role("link", name=album_title).click()
    expect(page.get_by_role("heading", name=album_title, level=1)).to_be_visible()


def test_empty_and_unmatched_queries_have_their_own_states(page: Page, run_token: str) -> None:
    """F10: guidance for an empty query, an explicit dead end for a miss."""
    page.goto("/search")
    expect(page.get_by_text(ru("search.prompt_title"))).to_be_visible()
    expect(page.get_by_text(ru("search.prompt_note"))).to_be_visible()

    page.goto(f"/search?q=нетничего{run_token}")
    expect(page.get_by_text(ru("search.empty_title"))).to_be_visible()


def test_an_unpublished_album_is_absent_from_search(
    page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """F26: publishing is what puts an album into `/photo` *and* into search."""
    album = trash.album(admin_api.create_album(f"E2E черновик {run_token}"))

    page.goto(f"/search?q={run_token}")
    expect(page.get_by_text(ru("search.empty_title"))).to_be_visible()

    admin_api.publish_album(album)
    page.goto(f"/search?q={run_token}")
    expect(page.get_by_role("link", name=album.title)).to_be_visible()
