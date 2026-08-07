"""T072 — performance of a 50-photo album grid.

Budgets from SPEC "Non-functional → Performance":
  * CLS ≈ 0 on grid load
  * grid thumbnails ≤ ~120 KB each
  * LCP under 2.5 s
  * lazy loading and intrinsic dimensions actually in effect

Everything is measured in the page with the same APIs a field tool would use
(PerformanceObserver, Resource Timing) and written to `docs/qa/perf-50.json`.
The numbers are localhost, unthrottled — that is what "locally" in the budget
means, and it is the optimistic end of the range.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Playwright

from e2e.conftest import Trash, wait_for_ready
from e2e.helpers import AdminApi, Album, Post, photo_bytes, ru

pytestmark = pytest.mark.perf

PHOTO_COUNT = 50
CLS_BUDGET = 0.02  # "≈ 0"; 0.1 is Google's "good" line, this is far stricter
THUMB_BUDGET_KB = 120
LCP_BUDGET_MS = 2500

#: Throttle for the article measurement. A shift only exists in the window
#: between the text painting and the picture landing on top of it; on an
#: unthrottled localhost that window is too small to catch a real regression.
ARTICLE_KBPS = 400

# Installed before any page script so nothing is missed between navigation and
# the first paint.
INSTRUMENT = """
window.__cls = 0;
window.__shifts = [];
window.__lcp = 0;
new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (entry.hadRecentInput) continue;
    window.__cls += entry.value;
    window.__shifts.push({
      value: entry.value,
      sources: (entry.sources || []).map((s) =>
        s.node ? (s.node.tagName || '') + '.' + (s.node.className || '') : '?')
    });
  }
}).observe({ type: 'layout-shift', buffered: true });
new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    window.__lcp = entry.startTime;
    window.__lcpElement = entry.element
      ? entry.element.tagName + '.' + (entry.element.className || '')
      : null;
    window.__lcpSize = entry.size;
  }
}).observe({ type: 'largest-contentful-paint', buffered: true });
"""


@pytest.fixture
def big_album(playwright: Playwright, base_url: str, admin_storage_state: str) -> Iterator[Album]:
    """A published album of 50 processed photos, torn down afterwards.

    Ten distinct frames cycled five times: generating fifty different noise
    fields costs more host CPU than it buys in measurement fidelity, and the
    derivative sizes below are still the real pipeline's output.
    """
    request = playwright.request.new_context(base_url=base_url, storage_state=admin_storage_state)
    api = AdminApi(request)
    album = api.create_album("E2E перф 50 фото", "Пятьдесят кадров для замера")
    try:
        for index in range(PHOTO_COUNT):
            api.upload_photo(album, photo_bytes(1800, 1200, seed=index % 10), f"perf-{index}.jpg")
        wait_for_ready(api, album, PHOTO_COUNT, timeout_s=600)
        api.publish_album(album)
        yield album
    finally:
        api.delete_album(album.id)
        request.dispose()


def test_the_50_photo_grid_meets_its_budgets(
    browser: Browser, base_url: str, qa_dir: Path, big_album: Album
) -> None:
    # A cold context: a warm HTTP cache would report a transfer size of zero.
    context = browser.new_context(base_url=base_url, viewport={"width": 1440, "height": 900})
    try:
        page = context.new_page()
        page.add_init_script(INSTRUMENT)
        page.goto(f"/photo/{big_album.slug}", wait_until="load")
        page.wait_for_load_state("networkidle")

        grid = page.get_by_role("list", name=ru("photo.grid_label"))
        assert grid.get_by_role("listitem").count() == PHOTO_COUNT

        above_the_fold = page.evaluate(
            """
            () => {
              const imgs = Array.from(document.querySelectorAll('.photo-item img'));
              return {
                total: imgs.length,
                lazy: imgs.filter((i) => i.getAttribute('loading') === 'lazy').length,
                withDimensions: imgs.filter(
                  (i) => i.getAttribute('width') > 0 && i.getAttribute('height') > 0).length,
                withSrcset: imgs.filter(
                  (i) => (i.getAttribute('srcset') || '').includes('w')).length,
                withAlt: imgs.filter((i) => (i.getAttribute('alt') || '').trim().length > 0).length,
                loaded: imgs.filter((i) => i.complete && i.naturalWidth > 0).length
              };
            }
            """
        )

        settled = page.evaluate(
            "() => ({ cls: window.__cls, shifts: window.__shifts, lcp: window.__lcp,"
            " element: window.__lcpElement || null, size: window.__lcpSize || 0 })"
        )

        media = page.evaluate(
            """
            () => performance.getEntriesByType('resource')
              .filter((r) => r.name.includes('/media/'))
              .map((r) => ({
                url: r.name.split('/').pop(),
                transferKB: +(r.transferSize / 1024).toFixed(1),
                encodedKB: +(r.encodedBodySize / 1024).toFixed(1),
                ms: Math.round(r.duration)
              }))
            """
        )

        # JPEG and clipped: the synthetic frames are pure entropy and a
        # full-page PNG of them costs 1.5 MB of repository for one screenshot.
        page.screenshot(
            path=str(qa_dir / "album-50-grid.jpg"),
            type="jpeg",
            quality=70,
            clip={"x": 0, "y": 0, "width": 1440, "height": 900},
        )

        # Scroll to the end: the deferred images must load, not merely be skipped.
        page.evaluate(
            "() => new Promise((done) => {"
            "  let y = 0;"
            "  const step = () => {"
            "    y += window.innerHeight;"
            "    window.scrollTo(0, y);"
            "    if (y < document.body.scrollHeight) setTimeout(step, 120); else done();"
            "  };"
            "  step();"
            "})"
        )
        page.wait_for_load_state("networkidle")
        after_scroll = page.evaluate(
            """
            () => {
              const imgs = Array.from(document.querySelectorAll('.photo-item img'));
              return {
                loaded: imgs.filter((i) => i.complete && i.naturalWidth > 0).length,
                mediaRequests: performance.getEntriesByType('resource')
                  .filter((r) => r.name.includes('/media/')).length
              };
            }
            """
        )
        cls_after_scroll = page.evaluate("() => window.__cls")
    finally:
        context.close()

    heaviest = max(media, key=lambda r: r["encodedKB"]) if media else None
    report = {
        "photos": PHOTO_COUNT,
        "viewport": "1440x900",
        "cls_on_load": round(settled["cls"], 5),
        "cls_after_scrolling_to_the_end": round(cls_after_scroll, 5),
        "shifts": settled["shifts"],
        "lcp_ms": round(settled["lcp"]),
        "lcp_element": settled["element"],
        "images": above_the_fold,
        "images_after_scroll": after_scroll,
        "media_requests_on_load": len(media),
        "heaviest_media_kb": heaviest,
        "media": sorted(media, key=lambda r: -r["encodedKB"])[:10],
        "budgets": {
            "cls": CLS_BUDGET,
            "thumbnail_kb": THUMB_BUDGET_KB,
            "lcp_ms": LCP_BUDGET_MS,
        },
    }
    (qa_dir / "perf-50.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # -- intrinsic dimensions and lazy loading, actually in effect ---------
    assert above_the_fold["total"] == PHOTO_COUNT
    assert above_the_fold["withDimensions"] == PHOTO_COUNT, above_the_fold
    assert above_the_fold["lazy"] == PHOTO_COUNT, above_the_fold
    assert above_the_fold["withSrcset"] == PHOTO_COUNT, above_the_fold
    assert above_the_fold["withAlt"] == PHOTO_COUNT, above_the_fold
    # Lazy means fewer than all fifty were fetched before scrolling…
    assert len(media) < PHOTO_COUNT, f"all {len(media)} thumbnails were fetched up front"
    # …and that the rest arrive once they are needed.
    assert after_scroll["mediaRequests"] > len(media), after_scroll

    # -- layout stability ---------------------------------------------------
    assert settled["cls"] <= CLS_BUDGET, report["shifts"]
    assert cls_after_scroll <= CLS_BUDGET, report["shifts"]

    # -- weight -------------------------------------------------------------
    assert heaviest is not None
    over_budget = [r for r in media if r["encodedKB"] > THUMB_BUDGET_KB]
    assert not over_budget, over_budget

    # -- LCP ----------------------------------------------------------------
    assert 0 < settled["lcp"] <= LCP_BUDGET_MS, settled


# ---------------------------------------------------------------------------
# Pictures inside an article (F9)
#
# The album grid above is stable because the photo templates emit intrinsic
# dimensions. Pictures written into an article go through
# `app/services/markdown.py` instead, which emitted none: two of them measured
# CLS 0.119 against the same 0.02 budget, the text below them jumping as each
# lazy picture arrived. This is the regression test for that.
# ---------------------------------------------------------------------------
@pytest.fixture
def illustrated_article(admin_api: AdminApi, trash: Trash, run_token: str) -> Post:
    """A published article with two pictures and text under each of them.

    Portrait, because that is the shape that hurts: at the prose column's width
    an unreserved 2:3 frame shoves most of a viewport's worth of text down when
    it lands, where an unreserved landscape one barely leaves the budget.
    """
    post = trash.post(admin_api.create_post(f"E2E вёрстка {run_token}"))
    urls = [
        admin_api.upload_inline_image(
            post, photo_bytes(1600, 2400, seed=index), f"prose-{run_token}-{index}.jpg"
        )
        for index in range(2)
    ]
    # Enough prose under each picture that a shift has something to move.
    paragraph = "Текст под картинкой, которому положено стоять на месте. " * 12
    admin_api.publish_post(
        post,
        "\n\n".join(
            [paragraph, f"![Кадр один]({urls[0]})", paragraph, f"![Кадр два]({urls[1]})", paragraph]
        ),
    )
    return post


def test_an_illustrated_article_reserves_room_for_its_pictures(
    browser: Browser, base_url: str, qa_dir: Path, illustrated_article: Post
) -> None:
    context = browser.new_context(base_url=base_url, viewport={"width": 1440, "height": 900})
    try:
        page = context.new_page()
        page.add_init_script(INSTRUMENT)

        cdp = context.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send(
            "Network.emulateNetworkConditions",
            {
                "offline": False,
                "latency": 40,
                "downloadThroughput": ARTICLE_KBPS * 1024,
                "uploadThroughput": ARTICLE_KBPS * 1024,
            },
        )

        page.goto(f"/blog/{illustrated_article.slug}", wait_until="load")
        page.wait_for_load_state("networkidle")
        cls_on_load = page.evaluate("() => window.__cls")

        # The second picture is below the fold and lazy: it can only shift the
        # page once something scrolls it into view.
        page.evaluate(
            "() => new Promise((done) => {"
            "  let y = 0;"
            "  const step = () => {"
            "    y += window.innerHeight;"
            "    window.scrollTo(0, y);"
            "    if (y < document.body.scrollHeight) setTimeout(step, 200); else done();"
            "  };"
            "  step();"
            "})"
        )
        page.wait_for_load_state("networkidle")

        settled = page.evaluate(
            "() => ({ cls: window.__cls, shifts: window.__shifts, lcp: window.__lcp,"
            " element: window.__lcpElement || null })"
        )
        pictures = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('.prose img')).map((i) => ({
              width: i.getAttribute('width'),
              height: i.getAttribute('height'),
              loading: i.getAttribute('loading'),
              srcset: !!i.getAttribute('srcset'),
              loaded: i.complete && i.naturalWidth > 0
            }))
            """
        )
    finally:
        context.close()

    report = {
        "pictures": len(pictures),
        "viewport": "1440x900",
        "throughput_kbps": ARTICLE_KBPS,
        "cls_on_load": round(cls_on_load, 5),
        "cls_after_scrolling_to_the_end": round(settled["cls"], 5),
        "shifts": settled["shifts"],
        "lcp_ms": round(settled["lcp"]),
        "lcp_element": settled["element"],
        "images": pictures,
        "budgets": {"cls": CLS_BUDGET},
        "was_before_the_fix": 0.119,
    }
    (qa_dir / "perf-article.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    assert len(pictures) == 2, pictures
    for picture in pictures:
        # The cause, asserted directly: a ratio the browser can reserve before
        # a single byte of the picture has arrived.
        assert picture["width"] and int(picture["width"]) > 0, pictures
        assert picture["height"] and int(picture["height"]) > 0, pictures
        assert picture["loaded"], pictures

    assert cls_on_load <= CLS_BUDGET, report["shifts"]
    assert settled["cls"] <= CLS_BUDGET, report["shifts"]
