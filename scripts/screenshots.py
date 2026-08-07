"""Capture the README's screenshots from the running site.

A picture in a README goes stale the moment the design moves, and a stale one
is worse than none. This regenerates the whole set from the live development
stack, so refreshing them is one command rather than an afternoon of cropping.

Both themes, because the site has two and choosing one to show would misreport
it. The theme is emulated through `prefers-color-scheme` rather than clicked:
`theme.js` pins an explicit choice into `localStorage`, and a fresh context has
none, so the media query is what decides.

    make up
    uv run python scripts/screenshots.py

Writes `docs/qa/screenshots/<page>-<theme>.jpg`. JPEG at quality 82: these are
photographs of photographs, and a PNG set costs several megabytes of repository
for no visible gain.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "qa" / "screenshots"
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

VIEWPORT = {"width": 1440, "height": 900}

#: The four sections the README introduces, in the order it introduces them.
PAGES = (
    ("home", "/"),
    ("photo", "/photo"),
    ("blog", "/blog"),
    ("dev", "/dev"),
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for theme in ("light", "dark"):
                context = browser.new_context(
                    base_url=BASE_URL, viewport=VIEWPORT, color_scheme=theme
                )
                page = context.new_page()
                for name, path in PAGES:
                    page.goto(path, wait_until="load")
                    page.wait_for_load_state("networkidle")
                    target = OUT / f"{name}-{theme}.jpg"
                    page.screenshot(
                        path=str(target),
                        type="jpeg",
                        quality=82,
                        clip={"x": 0, "y": 0, **VIEWPORT},
                    )
                    written.append(target)
                context.close()
        finally:
            browser.close()

    for path in written:
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")
    print(f"\n{len(written)} screenshots written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
