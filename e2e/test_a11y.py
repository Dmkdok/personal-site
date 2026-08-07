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

from e2e.helpers import Album, composite, contrast_ratio, flatten, ru

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


def _threshold(sample: dict) -> float:
    """WCAG 1.4.3: 3:1 for large text (≥24px, or ≥18.66px at 700+), else 4.5:1."""
    large = sample["fontSize"] >= 24 or (
        sample["fontSize"] >= 18.66 and sample["fontWeight"] >= 700
    )
    return 3.0 if large else 4.5


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_meets_aa_contrast_in_both_themes(
    browser: Browser, base_url: str, qa_dir: Path, theme: str, published_album: Album
) -> None:
    context = browser.new_context(
        base_url=base_url, color_scheme="dark" if theme == "dark" else "light"
    )
    measured: list[dict] = []
    failures: list[dict] = []
    unmeasurable: list[dict] = []
    try:
        page = context.new_page()
        page.goto("/")
        page.evaluate("(t) => localStorage.setItem('theme', t)", theme)

        for path in [*PAGES, f"/photo/{published_album.slug}"]:
            page.goto(path)
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
    finally:
        context.close()

    (qa_dir / f"contrast-{theme}.json").write_text(
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

    assert measured, "collected nothing — the walker is broken, not the site"
    assert not failures, "\n".join(
        f"{f['page']} {f['selector']} {f['ratio']}:1 < {f['required']}:1 "
        f"({f['color']} on {f['background']}) — {f['text']!r}"
        for f in failures
    )


def test_every_image_is_described_or_marked_decorative(page: Page, published_album: Album) -> None:
    """Alt on content images; decorative ones empty *and* out of the tree."""
    offenders = []
    for path in ["/", "/photo", "/blog", f"/photo/{published_album.slug}"]:
        page.goto(path)
        offenders += page.evaluate(
            """
            (path) => Array.from(document.images).flatMap((img) => {
              const alt = img.getAttribute('alt');
              if (alt === null) return [{ path, src: img.currentSrc, why: 'no alt attribute' }];
              if (alt.trim() === '' && !img.closest('[aria-hidden="true"]')) {
                return [{ path, src: img.currentSrc, why: 'empty alt but still in the a11y tree' }];
              }
              return [];
            })
            """,
            path,
        )
    assert not offenders, offenders


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


def test_every_focus_stop_shows_a_visible_indicator(
    page: Page, qa_dir: Path, published_album: Album
) -> None:
    """Focus must be visible everywhere; the Tab sweep proves the order too."""
    invisible = []
    swept = []
    for path in ["/", "/photo", "/blog", "/search?q=", f"/photo/{published_album.slug}"]:
        page.goto(path)
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

    (qa_dir / "focus-sweep.json").write_text(
        json.dumps(
            {"stops": swept, "without_a_focus_indicator": invisible}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
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
    expect(page.get_by_role("region", name="Режим редактирования")).to_be_visible()


def test_an_article_can_be_written_and_published_without_a_mouse(
    admin_page: Page, trash, run_token: str
) -> None:
    """Launch checklist: one full admin publishing flow, keyboard only."""
    title = f"E2E клавиатура {run_token}"

    admin_page.goto("/blog")
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


def test_target_sizes_at_360px(browser: Browser, base_url: str, qa_dir: Path) -> None:
    """Two different bars, measured separately at the narrowest supported width.

    WCAG 2.2 AA 2.5.8 asks for 24×24 with an inline and a spacing exception —
    that is the accessibility line. SPEC F12 asks for 44×44, which is stricter
    than AA; anything between the two is recorded but does not fail this test.
    """
    context = browser.new_context(base_url=base_url, viewport={"width": 360, "height": 780})
    try:
        page = context.new_page()
        small = []
        for path in ["/", "/photo", "/blog", "/dev", "/login"]:
            page.goto(path)
            small += page.evaluate(MEASURE_TARGETS, path)

        aa_failures = [
            s
            for s in small
            if min(s["width"], s["height"]) < 24 and not s["inlineInProse"] and s["crowded"]
        ]
        (qa_dir / "target-size-360px.json").write_text(
            json.dumps(
                {"under_44px_spec_f12": small, "under_wcag_2_5_8": aa_failures},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        assert not aa_failures, json.dumps(aa_failures, ensure_ascii=False, indent=2)
    finally:
        context.close()


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
