"""T071 — accessibility pass.

Four things the launch checklist asks for, measured rather than asserted by
inspection: AA contrast in both themes, keyboard-only completion of every flow,
`prefers-reduced-motion`, and alt text plus visible focus.

Contrast numbers land in `docs/qa/contrast.json` so the ratios can be argued
with instead of taken on trust.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, expect

from e2e.conftest import Trash
from e2e.helpers import (
    AdminApi,
    Album,
    composite,
    contrast_ratio,
    flatten,
    ru,
    switch_mode,
)

pytestmark = pytest.mark.a11y

# Walks every element that paints text of its own, resolves the effective
# backdrop by climbing until something opaque is found, and reports the pair.
# Elements sitting on an image or a gradient are reported as unmeasurable
# rather than quietly counted as a pass.
COLLECT_TEXT_COLOURS = """
() => {
  const out = [];
  const seen = new Set();

  function ownText(el) {
    for (const node of el.childNodes) {
      if (node.nodeType === 3 && node.textContent.trim().length > 1) return true;
    }
    return false;
  }

  function describe(el) {
    let path = el.tagName.toLowerCase();
    if (el.id) path += '#' + el.id;
    else if (el.className && typeof el.className === 'string') {
      path += '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.');
    }
    return path;
  }

  for (const el of document.querySelectorAll('body *')) {
    if (!ownText(el)) continue;
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    if (parseFloat(style.opacity) === 0) continue;
    const box = el.getBoundingClientRect();
    if (box.width < 1 || box.height < 1) continue;
    // .visually-hidden text is clipped to 1px and never read by eye.
    if (box.width <= 2 && box.height <= 2) continue;
    if (el.closest('[aria-hidden="true"]')) continue;

    // Every translucent layer between the text and the first opaque surface,
    // topmost first. Python composites them; picking only the first opaque one
    // would ignore the tints stacked above it.
    const backdrop = [];
    let imaged = false;
    let opaque = false;
    for (let node = el; node; node = node.parentElement) {
      const s = getComputedStyle(node);
      if (s.backgroundImage && s.backgroundImage !== 'none') imaged = true;
      const bg = s.backgroundColor;
      if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
        backdrop.push(bg);
        const alpha = bg.includes('/')
          ? parseFloat(bg.split('/')[1])
          : (bg.startsWith('rgba') ? parseFloat(bg.split(',')[3]) : 1);
        if (alpha >= 1) { opaque = true; break; }
      }
    }
    if (!opaque) backdrop.push(getComputedStyle(document.documentElement).backgroundColor);

    const size = parseFloat(style.fontSize);
    const weight = parseInt(style.fontWeight, 10) || 400;
    const key = describe(el) + '|' + style.color + '|' + backdrop.join('+') + '|' + size;
    if (seen.has(key)) continue;
    seen.add(key);

    out.push({
      selector: describe(el),
      text: el.textContent.trim().slice(0, 60),
      color: style.color,
      backdrop: backdrop,
      background: backdrop[backdrop.length - 1],
      fontSize: size,
      fontWeight: weight,
      onImage: imaged
    });
  }
  return out;
}
"""

PAGES = ["/", "/dev", "/photo", "/blog", "/search?q=", "/login", "/does-not-exist"]

# The owner's controls are not on the page in «Просмотр» at all (ADR-028), and
# every walker below skips what has no box — so an unswitched admin sweep would
# measure everything except the markup it was extended to measure (F-001).
#
# It used to force `opacity: 1` through the CSSOM, because the CSP is
# `style-src 'self'` and an injected <style> is dropped silently. Now it clicks
# the switch instead: the sweeps measure the real «Правка» state rather than a
# simulation of it, which is the one place this change makes a test stricter
# rather than merely different. The count still comes back so a test can fail
# when nothing was revealed — and it counts *rendered* affordances, not DOM
# nodes, because in «Просмотр» every node is still there.
#
# The owner's menu is opened by clicking its button rather than by unsetting
# `hidden`, so the sweeps measure the state the product produces. Its contents
# were swept before ADR-027 too — they were in the admin bar, which was always
# on the page — and they are still the owner's controls, so they are still in.
REVEAL_ADMIN_AFFORDANCES = """
() => {
  let revealed = 0;
  const toggle = document.querySelector('[data-owner-menu-toggle]');
  const panel = document.getElementById('owner-menu');
  if (toggle && panel && panel.hidden) {
    toggle.click();
    if (!panel.hidden) revealed += 1;
  }
  const edit = document.querySelector('[data-edit-mode="edit"]');
  if (edit) edit.click();
  for (const selector of ['.editable__edit', '.site-links__edit', '.photo-item__admin']) {
    for (const el of document.querySelectorAll(selector)) {
      if (el.getClientRects().length) revealed += 1;
    }
  }
  return revealed;
}
"""


def _threshold(sample: dict) -> float:
    """WCAG 1.4.3: 3:1 for large text (≥24px, or ≥18.66px at 700+), else 4.5:1."""
    large = sample["fontSize"] >= 24 or (
        sample["fontSize"] >= 18.66 and sample["fontWeight"] >= 700
    )
    return 3.0 if large else 4.5


def _sweep_contrast(
    context, paths: list[str], theme: str, *, reveal: bool
) -> tuple[list[dict], list[dict], list[dict], int]:
    """Walk `paths` in `theme` and return (measured, failures, unmeasurable, revealed).

    One walker and one `_threshold` for the anonymous and the signed-in sweep
    alike: the moment the admin side gets its own thresholds, it stops being
    measured and starts being asserted.
    """
    measured: list[dict] = []
    failures: list[dict] = []
    unmeasurable: list[dict] = []
    revealed = 0

    page = context.new_page()
    page.goto("/")
    page.evaluate("(t) => localStorage.setItem('theme', t)", theme)

    for path in paths:
        page.goto(path)
        if reveal:
            revealed += page.evaluate(REVEAL_ADMIN_AFFORDANCES)
        for sample in page.evaluate(COLLECT_TEXT_COLOURS):
            fg = flatten(sample["color"], sample["backdrop"])
            bg = composite(sample["backdrop"])
            sample |= {
                "page": path,
                "theme": theme,
                "ratio": round(contrast_ratio(fg, bg), 2),
                "required": _threshold(sample),
            }
            measured.append(sample)
            if sample["onImage"]:
                unmeasurable.append(sample)
            elif sample["ratio"] < sample["required"]:
                failures.append(sample)

    return measured, failures, unmeasurable, revealed


def _write_contrast(
    qa_dir: Path,
    name: str,
    theme: str,
    measured: list[dict],
    failures: list[dict],
    unmeasurable: list[dict],
) -> None:
    (qa_dir / name).write_text(
        json.dumps(
            {
                "theme": theme,
                "samples": len(measured),
                "failures": failures,
                "unmeasurable": unmeasurable,
                "worst": sorted(measured, key=lambda s: s["ratio"])[:12],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _contrast_report(failures: list[dict]) -> str:
    return "\n".join(
        f"{f['page']} {f['selector']} {f['ratio']}:1 < {f['required']}:1 "
        f"({f['color']} on {f['background']}) — {f['text']!r}"
        for f in failures
    )


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_meets_aa_contrast_in_both_themes(
    browser: Browser, base_url: str, qa_dir: Path, theme: str, published_album: Album
) -> None:
    context = browser.new_context(
        base_url=base_url, color_scheme="dark" if theme == "dark" else "light"
    )
    try:
        measured, failures, unmeasurable, _ = _sweep_contrast(
            context, [*PAGES, f"/photo/{published_album.slug}"], theme, reveal=False
        )
    finally:
        context.close()

    _write_contrast(qa_dir, f"contrast-{theme}.json", theme, measured, failures, unmeasurable)

    assert measured, "collected nothing — the walker is broken, not the site"
    assert not failures, _contrast_report(failures)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_admin_text_meets_aa_contrast_in_both_themes(
    browser: Browser,
    base_url: str,
    qa_dir: Path,
    theme: str,
    admin_storage_state: str,
    admin_surfaces: list[str],
) -> None:
    """F-001: the surfaces the product exists to provide, on the same walker.

    Every gate in this file used to run anonymously, so the editor, the photo
    tile tools, the upload queue and the admin bar had never been measured at
    all — the four screens the owner actually lives in.
    """
    context = browser.new_context(
        base_url=base_url,
        color_scheme="dark" if theme == "dark" else "light",
        storage_state=admin_storage_state,
    )
    try:
        measured, failures, unmeasurable, revealed = _sweep_contrast(
            context, admin_surfaces, theme, reveal=True
        )
    finally:
        context.close()

    _write_contrast(qa_dir, f"contrast-admin-{theme}.json", theme, measured, failures, unmeasurable)

    assert measured, "collected nothing — the walker is broken, not the site"
    assert revealed, "the sweep found no owner affordance on the page; it never entered «Правка»"
    assert not failures, _contrast_report(failures)


COLLECT_UNDESCRIBED_IMAGES = """
(path) => Array.from(document.images).flatMap((img) => {
  const alt = img.getAttribute('alt');
  if (alt === null) return [{ path, src: img.currentSrc, why: 'no alt attribute' }];
  if (alt.trim() === '' && !img.closest('[aria-hidden="true"]')) {
    return [{ path, src: img.currentSrc, why: 'empty alt but still in the a11y tree' }];
  }
  return [];
})
"""


def _sweep_alt_text(page: Page, paths: list[str]) -> list[dict]:
    offenders: list[dict] = []
    for path in paths:
        page.goto(path)
        offenders += page.evaluate(COLLECT_UNDESCRIBED_IMAGES, path)
    return offenders


def test_every_image_is_described_or_marked_decorative(page: Page, published_album: Album) -> None:
    """Alt on content images; decorative ones empty *and* out of the tree."""
    offenders = _sweep_alt_text(page, ["/", "/photo", "/blog", f"/photo/{published_album.slug}"])
    assert not offenders, offenders


def test_every_admin_image_is_described_or_marked_decorative(
    admin_page: Page, admin_surfaces: list[str]
) -> None:
    """F-001: the editor's cover and the tile thumbnails were never swept."""
    assert not _sweep_alt_text(admin_page, admin_surfaces)


def test_reduced_motion_removes_transitions(browser: Browser, base_url: str) -> None:
    """CONVENTIONS: motion under 250 ms, and none at all under reduced motion."""
    context = browser.new_context(base_url=base_url, reduced_motion="reduce")
    try:
        page = context.new_page()
        page.goto("/")
        durations = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('body *'))
              .map((el) => getComputedStyle(el))
              .flatMap((s) => [...s.transitionDuration.split(','),
                               ...s.animationDuration.split(',')])
              .map((v) => parseFloat(v) * (v.includes('ms') ? 1 : 1000))
              .filter((ms) => ms > 1)
            """
        )
        assert durations == [], f"{len(durations)} animated properties survive reduced motion"
    finally:
        context.close()


def test_motion_stays_under_250ms_by_default(page: Page) -> None:
    page.goto("/")
    slowest = page.evaluate(
        """
        () => Math.max(0, ...Array.from(document.querySelectorAll('body *'))
          .map((el) => getComputedStyle(el))
          .flatMap((s) => [...s.transitionDuration.split(','), ...s.animationDuration.split(',')])
          .map((v) => parseFloat(v) * (v.includes('ms') ? 1 : 1000))
          .filter((ms) => Number.isFinite(ms)))
        """
    )
    assert slowest <= 250, f"slowest transition/animation is {slowest} ms"


def test_a_disabled_button_looks_disabled(page: Page) -> None:
    """UI-AUDIT F-005: unavailable must not look identical to available.

    `.button` sets `color` explicitly, so the browser's own greying never
    applied and a disabled control was pixel-identical to a working one. The
    treatment now lives once, in `components.css`. Measured against the shipped
    stylesheet rather than read out of it — a grep would pass on a rule that the
    cascade never reaches.
    """
    page.goto("/")
    measured = page.evaluate(
        """
        () => {
          const make = (disabled) => {
            const el = document.createElement('button');
            el.className = 'button button--quiet';
            el.textContent = 'x';
            el.disabled = disabled;
            document.body.appendChild(el);
            return el;
          };
          const live = make(false);
          const dead = make(true);
          const style = getComputedStyle(dead);
          const result = {
            live: getComputedStyle(live).opacity,
            dead: style.opacity,
            cursor: style.cursor
          };
          live.remove();
          dead.remove();
          return result;
        }
        """
    )
    assert measured["live"] == "1", measured
    assert float(measured["dead"]) < 1, measured
    assert measured["cursor"] == "not-allowed", measured


READ_ROLE = """
(el) => {
  const s = getComputedStyle(el);
  return {
    transform: s.textTransform,
    tracking: s.letterSpacing,
    color: s.color,
    family: s.fontFamily
  };
}
"""


def test_the_three_label_roles_are_told_apart(
    admin_page: Page,
    admin_surfaces: list[str],
    admin_api: AdminApi,
    trash: Trash,
    run_token: str,
) -> None:
    """UI-AUDIT F-009: one costume was worn by ten jobs at once.

    Mono + uppercase + tracking + `--text-faint` dressed the eyebrow, every
    form label and every date alike, and on the editor screen seven of them
    ranked identically. Read off the shipped stylesheet rather than grepped:
    the point is what the cascade produces, not what the file says.
    """
    editor = next(path for path in admin_surfaces if path.endswith("/edit"))
    admin_page.goto(editor)
    eyebrow = admin_page.locator(".label").first.evaluate(READ_ROLE)
    field = admin_page.locator(".field__label").first.evaluate(READ_ROLE)

    assert eyebrow["transform"] == "uppercase", eyebrow
    assert eyebrow["tracking"] != "normal", eyebrow

    # The label the owner reads while typing: sentence case, and the body's own
    # tracking rather than the label's +0.09em — measured in px against the
    # eyebrow, since the inherited value is not the keyword `normal`.
    assert field["transform"] == "none", field
    assert float(field["tracking"].removesuffix("px")) <= 0, field
    assert "mono" in field["family"].lower(), field

    # A heading must not be the faintest thing on the page it heads.
    assert eyebrow["color"] != field["color"], (eyebrow, field)

    # The third role, on the one surface that is certain to carry it: a
    # published article states its date.
    post = trash.post(admin_api.create_post(f"E2E роли {run_token}"))
    admin_api.publish_post(post, "Текст.")
    admin_page.goto(f"/blog/{post.slug}")
    meta = admin_page.locator("p.meta").first.evaluate(READ_ROLE)

    assert meta["transform"] == "none", meta
    assert meta["color"] != eyebrow["color"], (meta, eyebrow)


PRESS_PROBE = """
() => {
  const el = document.createElement('button');
  el.className = 'button';
  el.id = 'press-probe';
  el.textContent = 'x';
  document.getElementById('main').prepend(el);
}
"""

NEXT_FRAMES = """
() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))
"""

READ_PRESS_STATE = """
(el) => {
  const s = getComputedStyle(el);
  return {
    scale: s.scale,
    background: s.backgroundColor,
    active: el.matches(':active'),
    hover: el.matches(':hover')
  };
}
"""


def _press_state(context, path: str) -> tuple[dict, dict, dict]:
    """A `.button`'s computed state at rest, under the pointer, and pressed.

    Hovered is measured as well as resting because `.button:hover` already
    repaints the background: comparing a press against rest would pass on the
    hover alone, and prove nothing about `:active`.
    """
    page = context.new_page()
    page.goto(path)
    page.evaluate(PRESS_PROBE)
    probe = page.locator("#press-probe")
    resting = probe.evaluate(READ_PRESS_STATE)

    box = probe.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    # `.button` transitions its background, and reduced motion shortens that to
    # 0.01 ms rather than removing it — either way a value read in the same tick
    # as the pointer event is the value from before it. Two frames is the wait.
    page.evaluate(NEXT_FRAMES)
    hovered = probe.evaluate(READ_PRESS_STATE)

    page.mouse.down()
    page.evaluate(NEXT_FRAMES)
    pressed = probe.evaluate(READ_PRESS_STATE)
    page.mouse.up()
    return resting, hovered, pressed


def test_a_pressed_button_answers_the_press(browser: Browser, base_url: str) -> None:
    """UI-AUDIT F-023: feedback before the response, not instead of it.

    An htmx save takes 100–300 ms, and until it lands the only thing that can
    tell the owner the press registered is the button. Measured with a real
    pointer press against the shipped stylesheet: `:active` cannot be forced
    from script, and a grep would pass on a rule the cascade never reaches.
    """
    context = browser.new_context(base_url=base_url)
    try:
        resting, hovered, pressed = _press_state(context, "/")
    finally:
        context.close()

    assert resting["scale"] == "none", resting
    assert hovered["scale"] == "none", hovered
    assert pressed["scale"] != "none", pressed
    assert float(pressed["scale"].split()[0]) < 1, pressed


def test_a_pressed_button_answers_without_moving_under_reduced_motion(
    browser: Browser, base_url: str
) -> None:
    """The same feedback, expressed as colour where movement is unwelcome."""
    context = browser.new_context(base_url=base_url, reduced_motion="reduce")
    try:
        _, hovered, pressed = _press_state(context, "/")
    finally:
        context.close()

    # `none` is the unset value and `1` the explicit override; both are "the
    # button did not move", which is the whole of what this asks.
    assert pressed["scale"] in ("none", "1"), pressed
    assert pressed["background"] != hovered["background"], (hovered, pressed)


# WCAG 2.4.7 is "the indicator is visible", not "the element has an outline":
# the search field paints its ring on the wrapping label via :focus-within. So
# the stop is compared against itself unfocused, two levels up, and anything
# that changed counts.
SNAPSHOT_FOCUS = """
() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  window.__stops = [el, el.parentElement, el.parentElement && el.parentElement.parentElement]
    .filter(Boolean);
  window.__snap = (n) => {
    const s = getComputedStyle(n);
    return [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.borderColor,
            s.borderWidth, s.backgroundColor, s.color, s.textDecorationLine].join('|');
  };
  const box = el.getBoundingClientRect();
  return {
    tag: el.tagName.toLowerCase(),
    id: el.id || null,
    label: (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 40),
    visible: box.width > 0 && box.height > 0,
    focused: window.__stops.map(window.__snap)
  };
}
"""

SNAPSHOT_RESTING = """
() => {
  const el = window.__stops[0];
  el.blur();
  const resting = window.__stops.map(window.__snap);
  el.focus();
  return resting;
}
"""


def _sweep_focus(
    page: Page, paths: list[str], *, reveal: bool
) -> tuple[list[dict], list[dict], int]:
    """Tab through each page and return (stops, stops without an indicator, revealed)."""
    invisible: list[dict] = []
    swept: list[dict] = []
    revealed = 0

    for path in paths:
        page.goto(path)
        if reveal:
            revealed += page.evaluate(REVEAL_ADMIN_AFFORDANCES)
        page.evaluate("() => document.body.focus()")
        for _ in range(60):
            page.keyboard.press("Tab")
            state = page.evaluate(SNAPSHOT_FOCUS)
            if state is None:
                break
            resting = page.evaluate(SNAPSHOT_RESTING)
            changed = [f != r for f, r in zip(state["focused"], resting, strict=False)]
            record = {
                "page": path,
                "tag": state["tag"],
                "id": state["id"],
                "label": state["label"],
                "indicator_on": ["self", "parent", "grandparent"][changed.index(True)]
                if any(changed)
                else None,
            }
            swept.append(record)
            if state["visible"] and not any(changed):
                invisible.append(record | {"focused": state["focused"], "resting": resting})

    return swept, invisible, revealed


def _write_focus(qa_dir: Path, name: str, swept: list[dict], invisible: list[dict]) -> None:
    (qa_dir / name).write_text(
        json.dumps(
            {"stops": swept, "without_a_focus_indicator": invisible}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )


def test_every_focus_stop_shows_a_visible_indicator(
    page: Page, qa_dir: Path, published_album: Album
) -> None:
    """Focus must be visible everywhere; the Tab sweep proves the order too."""
    swept, invisible, _ = _sweep_focus(
        page,
        ["/", "/photo", "/blog", "/search?q=", f"/photo/{published_album.slug}"],
        reveal=False,
    )
    _write_focus(qa_dir, "focus-sweep.json", swept, invisible)
    assert not invisible, json.dumps(invisible, ensure_ascii=False, indent=2)


def test_every_admin_focus_stop_shows_a_visible_indicator(
    admin_page: Page, qa_dir: Path, admin_surfaces: list[str]
) -> None:
    """F-001: the editor, the tile toolbar and the admin bar, never swept before."""
    swept, invisible, revealed = _sweep_focus(admin_page, admin_surfaces, reveal=True)
    _write_focus(qa_dir, "focus-sweep-admin.json", swept, invisible)
    assert revealed, "the sweep found no owner affordance on the page; it never entered «Правка»"
    assert not invisible, json.dumps(invisible, ensure_ascii=False, indent=2)


def _tab_to(page: Page, text: str, limit: int = 40) -> None:
    """Tab until the focused control's accessible text matches, or give up loudly."""
    for _ in range(limit):
        page.keyboard.press("Tab")
        focused = page.evaluate(
            "() => (document.activeElement.getAttribute('aria-label')"
            " || document.activeElement.textContent || '').trim()"
        )
        if text in focused:
            return
    raise AssertionError(f"never reached {text!r} in {limit} tabs")


def test_login_is_completable_without_a_mouse(
    page: Page, admin_credentials: tuple[str, str]
) -> None:
    """Launch checklist: a keyboard-only pass through the login form."""
    username, password = admin_credentials
    page.goto("/login")
    # The username field carries autofocus; everything after it is typed.
    expect(page.get_by_label("Логин", exact=True)).to_be_focused()
    page.keyboard.type(username)
    page.keyboard.press("Tab")
    expect(page.get_by_label("Пароль", exact=True)).to_be_focused()
    page.keyboard.type(password)
    page.keyboard.press("Enter")  # implicit submission, no button hunt
    expect(page.get_by_role("button", name=ru("auth.owner_menu"), exact=True)).to_be_visible()


def test_an_article_can_be_written_and_published_without_a_mouse(
    admin_page: Page, trash, run_token: str
) -> None:
    """Launch checklist: one full admin publishing flow, keyboard only."""
    title = f"E2E клавиатура {run_token}"

    admin_page.goto("/blog")

    # Since I5 «Новая статья» is not on the page in «Просмотр» at all (ADR-032),
    # so entering «Правка» is the first step of the flow. Done from the keyboard
    # rather than through `switch_mode`, which clicks: this test's claim is that
    # the whole publishing flow is reachable without a mouse, and a mode switch
    # that needed one would make the claim false. Escape returns the caret to
    # the button that opened the menu (F-002), which is where tabbing on to the
    # page continues from.
    _tab_to(admin_page, ru("auth.owner_menu"))
    admin_page.keyboard.press("Enter")
    _tab_to(admin_page, ru("auth.mode_edit"), limit=6)
    admin_page.keyboard.press("Enter")
    admin_page.keyboard.press("Escape")
    expect(admin_page.locator("#owner-menu")).to_be_hidden()

    _tab_to(admin_page, ru("blog.new"))
    # htmx makes the swapped form visible and focuses it before it finishes
    # settling, and only a settled form has its submit intercepted. A human
    # cannot Tab and press Enter inside that ~20 ms window; synthetic keystrokes
    # can, and did — one run in three ended at `/blog?title=…`, the browser's
    # native GET. Wait for htmx's own lifecycle event instead of racing it.
    admin_page.evaluate(
        "() => { window.__settled = false;"
        " document.body.addEventListener('htmx:afterSettle',"
        " () => { window.__settled = true; }, { once: true }); }"
    )
    admin_page.keyboard.press("Enter")
    admin_page.wait_for_function("() => window.__settled === true")

    expect(admin_page.get_by_label(ru("blog.new_title_label"))).to_be_focused()
    admin_page.keyboard.type(title)
    _tab_to(admin_page, ru("blog.new_submit"), limit=5)
    admin_page.keyboard.press("Enter")

    expect(admin_page).to_have_url(re.compile(r"/blog/[^/]+/edit$"))
    post_id = int(admin_page.locator("#post-form").get_attribute("hx-post").rsplit("/", 1)[-1])
    trash.post_id(post_id)
    slug = admin_page.locator("#post-slug").input_value()

    admin_page.get_by_label(ru("blog.body_label")).focus()
    admin_page.keyboard.type("Написано с клавиатуры, без единого клика.")
    expect(admin_page.locator("#preview-body")).to_contain_text("без единого клика", timeout=5000)

    _tab_to(admin_page, ru("blog.publish"))
    admin_page.keyboard.press("Enter")
    expect(admin_page.locator("#editor-meta")).to_contain_text(ru("blog.status_published"))

    assert admin_page.request.get(f"/blog/{slug}").status == 200


def test_the_upload_picker_is_in_the_keyboard_tab_order(
    admin_page: Page, admin_api, trash, run_token: str
) -> None:
    """The drop zone is a pointer affordance; the labelled file input is not.

    Choosing files opens an operating-system dialog that Playwright replaces, so
    what is testable — and what matters — is that the control is labelled and
    reachable by Tab rather than drag-only.
    """
    album = trash.album(admin_api.create_album(f"E2E клавиатура {run_token}"))
    admin_page.goto(f"/photo/{album.slug}")
    # The zone is an owner-only block since I5 (ADR-032): reachable by Tab is a
    # claim about «Правка», which is the mode the owner uploads in.
    switch_mode(admin_page, "edit")

    picker = admin_page.get_by_label(ru("photo.choose_files_label"))
    expect(picker).to_be_visible()
    _tab_to_element(admin_page, picker)


def _tab_to_element(page: Page, locator, limit: int = 40) -> None:
    handle = locator.element_handle()
    for _ in range(limit):
        page.keyboard.press("Tab")
        if page.evaluate("(el) => document.activeElement === el", handle):
            return
    raise AssertionError("element was never reached by tabbing")


def test_the_skip_link_reaches_the_main_landmark(page: Page) -> None:
    page.goto("/")
    page.keyboard.press("Tab")
    skip = page.get_by_role("link", name=ru("site.skip"))
    expect(skip).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("main#main")).to_be_focused()


def test_the_navigation_pill_is_operable_from_the_keyboard(page: Page) -> None:
    """F1: section links, search and the theme toggle, all without a mouse."""
    page.goto("/blog")
    expect(page.get_by_role("link", name=ru("nav.blog"), exact=True)).to_have_attribute(
        "aria-current", "page"
    )

    page.get_by_role("link", name=ru("nav.photo"), exact=True).focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("heading", name=ru("photo.title"), level=1)).to_be_visible()
    expect(page.get_by_role("link", name=ru("nav.photo"), exact=True)).to_have_attribute(
        "aria-current", "page"
    )


MEASURE_TARGETS = """
(path) => {
  const targets = Array.from(
    document.querySelectorAll('a[href], button, input:not([type=hidden]), [role="button"]')
  ).filter((el) => el.offsetParent !== null || el.tagName === 'A')
   .map((el) => ({ el, box: el.getBoundingClientRect() }))
   .filter(({ box }) => box.width > 0 && box.height > 0);

  const centre = ({ box }) => ({ x: box.x + box.width / 2, y: box.y + box.height / 2 });

  return targets
    .filter(({ box }) => box.width < 44 || box.height < 44)
    .map((t) => {
      const c = centre(t);
      // WCAG 2.2 2.5.8 spacing exception, approximated by centre distance: a
      // 24px circle on this target must not reach another target's circle.
      const crowded = targets.some((other) => {
        if (other.el === t.el) return false;
        const o = centre(other);
        return Math.hypot(o.x - c.x, o.y - c.y) < 24;
      });
      return {
        path,
        tag: t.el.tagName.toLowerCase(),
        label: (t.el.getAttribute('aria-label') || t.el.textContent || '').trim().slice(0, 40),
        width: Math.round(t.box.width),
        height: Math.round(t.box.height),
        inlineInProse: !!t.el.closest('p, .prose, li.stack__item'),
        crowded
      };
    });
}
"""


def _sweep_targets(context, paths: list[str], *, reveal: bool) -> tuple[list[dict], int]:
    page = context.new_page()
    small: list[dict] = []
    revealed = 0
    for path in paths:
        page.goto(path)
        if reveal:
            revealed += page.evaluate(REVEAL_ADMIN_AFFORDANCES)
        small += page.evaluate(MEASURE_TARGETS, path)
    return small, revealed


def _under_wcag_258(small: list[dict]) -> list[dict]:
    return [
        s
        for s in small
        if min(s["width"], s["height"]) < 24 and not s["inlineInProse"] and s["crowded"]
    ]


def _write_targets(qa_dir: Path, name: str, small: list[dict], aa_failures: list[dict]) -> None:
    (qa_dir / name).write_text(
        json.dumps(
            {"under_44px_spec_f12": small, "under_wcag_2_5_8": aa_failures},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_target_sizes_at_360px(browser: Browser, base_url: str, qa_dir: Path) -> None:
    """Two different bars, measured separately at the narrowest supported width.

    WCAG 2.2 AA 2.5.8 asks for 24×24 with an inline and a spacing exception —
    that is the accessibility line. SPEC F12 asks for 44×44, which is stricter
    than AA; anything between the two is recorded but does not fail this test.
    """
    context = browser.new_context(base_url=base_url, viewport={"width": 360, "height": 780})
    try:
        small, _ = _sweep_targets(context, ["/", "/photo", "/blog", "/dev", "/login"], reveal=False)
    finally:
        context.close()

    aa_failures = _under_wcag_258(small)
    _write_targets(qa_dir, "target-size-360px.json", small, aa_failures)
    assert not aa_failures, json.dumps(aa_failures, ensure_ascii=False, indent=2)


def test_admin_target_sizes_at_360px(
    browser: Browser,
    base_url: str,
    qa_dir: Path,
    admin_storage_state: str,
    admin_surfaces: list[str],
) -> None:
    """F-001: the owner's controls at the narrowest width, measured for the first time.

    The same two bars as the anonymous sweep — 2.5.8 fails, F12 is recorded —
    because an admin control is not entitled to a smaller target than a
    visitor's one.
    """
    context = browser.new_context(
        base_url=base_url,
        viewport={"width": 360, "height": 780},
        storage_state=admin_storage_state,
    )
    try:
        small, revealed = _sweep_targets(context, admin_surfaces, reveal=True)
    finally:
        context.close()

    aa_failures = _under_wcag_258(small)
    _write_targets(qa_dir, "target-size-360px-admin.json", small, aa_failures)
    assert revealed, "the sweep found no owner affordance on the page; it never entered «Правка»"
    assert not aa_failures, json.dumps(aa_failures, ensure_ascii=False, indent=2)


# WCAG 2.4.11 asks that a focused control not be hidden by author-created
# content. The admin bar was that content — fixed to the bottom centre — and the
# document paid for it in two properties: `padding-block-end` on `.page` so the
# last control could be scrolled clear, and `scroll-padding-block-end` on the
# root so a tabbed-to one stopped above the bar rather than behind it (UI-AUDIT
# F-015). Together they made every signed-in page 88 px longer than a visitor's,
# at every width, which is the plain-language complaint ADR-027 came from.
#
# The bar is gone into the navigation capsule and both rules are deleted, so the
# question 2.4.11 asks has no subject any more: nothing is positioned over the
# end of the document. What is left to prove is that the clearance left nothing
# behind — this is that check, and it fails by exactly 88 px against the tree
# before ADR-027.
#
# Not a comparison of `scrollHeight`: the owner's page legitimately carries
# controls a visitor's does not — the upload zone, «Новый альбом» — so its total
# height is not a visitor's and is not meant to be. What must match is the empty
# space *after* the last element of the document, which is what the two rules
# created and what a visitor never had.
DOCUMENT_TAIL = """
() => {
  const root = document.documentElement;
  const footer = document.querySelector('.site-footer');
  return {
    owner: document.body.classList.contains('is-admin'),
    tail: Math.round(root.scrollHeight - (footer.getBoundingClientRect().bottom + window.scrollY)),
    scrollPadding: getComputedStyle(root).scrollPaddingBottom
  };
}
"""

CLEARANCE_PAGES = ["/", "/dev", "/blog", "/photo", "/search?q="]


def _document_tails(context, paths: list[str]) -> dict[str, dict]:
    page = context.new_page()
    measured: dict[str, dict] = {}
    for path in paths:
        page.goto(path)
        measured[path] = page.evaluate(DOCUMENT_TAIL)
    return measured


@pytest.mark.parametrize("width", [360, 1280])
def test_the_owners_document_reserves_no_clearance_a_visitors_does_not(
    browser: Browser,
    base_url: str,
    admin_storage_state: str,
    width: int,
) -> None:
    """F61 / ADR-027: nothing floats over the page, so nothing makes room for it.

    Both widths, because the clearance was width-independent: 88 px at 360 px
    and 88 px at 1280 px, on every page in the site.
    """
    viewport = {"width": width, "height": 780}
    visitor_context = browser.new_context(base_url=base_url, viewport=viewport)
    owner_context = browser.new_context(
        base_url=base_url, viewport=viewport, storage_state=admin_storage_state
    )
    try:
        visitor = _document_tails(visitor_context, CLEARANCE_PAGES)
        owner = _document_tails(owner_context, CLEARANCE_PAGES)
    finally:
        visitor_context.close()
        owner_context.close()

    for path in CLEARANCE_PAGES:
        mine, theirs = owner[path], visitor[path]
        assert mine["owner"], f"{path} did not render as the owner; this measured anonymously"
        # Sub-pixel layout rounds either way, hence the pixel of slack; the
        # regression this guards against is 88 of them.
        assert abs(mine["tail"]) <= 1, f"{path} at {width}px ends {mine['tail']}px after its footer"
        assert abs(mine["tail"] - theirs["tail"]) <= 1, (path, width, mine, theirs)
        assert mine["scrollPadding"] == theirs["scrollPadding"], (path, width, mine, theirs)


def test_no_console_errors_or_failed_requests_on_the_public_pages(
    page: Page, published_album: Album
) -> None:
    """Launch checklist: no console errors, no failed network requests."""
    problems: list[str] = []
    page.on(
        "console",
        lambda message: (
            problems.append(f"console {message.type}: {message.text}")
            if message.type == "error"
            else None
        ),
    )
    page.on("pageerror", lambda error: problems.append(f"pageerror: {error}"))
    page.on(
        "response",
        lambda response: (
            problems.append(f"{response.status} {response.url}") if response.status >= 400 else None
        ),
    )

    for path in ["/", "/dev", "/photo", "/blog", "/search?q=", f"/photo/{published_album.slug}"]:
        page.goto(path)
        page.wait_for_load_state("networkidle")

    assert not problems, problems
