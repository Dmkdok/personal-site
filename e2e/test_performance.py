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

from e2e.conftest import wait_for_ready
from e2e.helpers import AdminApi, Album, photo_bytes, ru

pytestmark = pytest.mark.perf

PHOTO_COUNT = 50
CLS_BUDGET = 0.02  # "≈ 0"; 0.1 is Google's "good" line, this is far stricter
THUMB_BUDGET_KB = 120
LCP_BUDGET_MS = 2500

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
