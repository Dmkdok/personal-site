"""Rasterise the site's «Dm» mark into everything that cannot take an SVG.

    uv run python scripts/icons.py

Writes `favicon-32.png`, `apple-touch-icon.png` (180 px), `favicon.ico` and
`og-default.png` (1200×630) beside `favicon.svg`. The SVG is the only place the
mark is drawn: rasterising it in a real browser is what keeps the fallbacks from
drifting away from it, which is what hand-redrawing the same monogram with
Pillow would invite.

Playwright is already a development dependency for the end-to-end suite, so
this adds nothing to the runtime image. The generated files are committed —
serving them is not allowed to depend on anyone having run this.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image
from playwright.sync_api import sync_playwright

from app.templating import translate

ICONS = Path(__file__).resolve().parent.parent / "app" / "static" / "icons"
SOURCE = ICONS / "favicon.svg"

#: The light-theme badge colour, so the PNGs match the SVG's default side.
PAGE = """
<!doctype html>
<meta name="color-scheme" content="light">
<style>html,body{margin:0;padding:0;background:transparent}
img{display:block;width:%(size)spx;height:%(size)spx}</style>
<img src="favicon.svg" alt="">
"""


def _render(size: int, target: Path) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": size, "height": size},
            device_scale_factor=1,
            color_scheme="light",
        )
        # Served from the icons directory so the relative <img src> resolves.
        (ICONS / "_icon-preview.html").write_text(PAGE % {"size": size}, encoding="utf-8")
        page.goto((ICONS / "_icon-preview.html").as_uri())
        page.wait_for_timeout(150)
        page.locator("img").screenshot(path=str(target), omit_background=True)
        browser.close()
    (ICONS / "_icon-preview.html").unlink(missing_ok=True)


#: The link-preview card. One fixed pair of colours rather than the theme's:
#: it is rendered once and shown on somebody else's surface, where nothing
#: knows or cares which theme the visitor prefers. The dark side is the safer
#: one — it reads on both a white and a black chat bubble.
OG_PAGE = """
<!doctype html>
<meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; }
  body {
    inline-size: 1200px; block-size: 630px;
    display: flex; flex-direction: column; justify-content: center;
    gap: 28px; padding: 0 96px; box-sizing: border-box;
    background: #1c1f23; color: #f2f4f7;
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  }
  img { inline-size: 132px; block-size: 132px; }
  h1 { margin: 0; font-size: 78px; font-weight: 800; letter-spacing: -1.5px; }
  p { margin: 0; font-size: 38px; font-weight: 500; color: #e0954a; }
</style>
<img src="favicon.svg" alt="">
<h1>%(name)s</h1>
<p>%(tagline)s</p>
"""


def _render_og(target: Path) -> None:
    page_path = ICONS / "_og-preview.html"
    page_path.write_text(
        OG_PAGE % {"name": translate("site.name"), "tagline": translate("site.tagline")},
        encoding="utf-8",
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1200, "height": 630},
            device_scale_factor=1,
            color_scheme="light",
        )
        page.goto(page_path.as_uri())
        page.wait_for_timeout(200)
        page.screenshot(path=str(target))
        browser.close()
    page_path.unlink(missing_ok=True)


def main() -> int:
    if not SOURCE.is_file():
        print(f"missing {SOURCE}", file=sys.stderr)
        return 1

    _render(32, ICONS / "favicon-32.png")
    _render(180, ICONS / "apple-touch-icon.png")
    _render_og(ICONS / "og-default.png")

    # A multi-size .ico for the browsers and pinned-tab lists that still ask for
    # one by its historic root path.
    with Image.open(ICONS / "apple-touch-icon.png") as source:
        source.save(ICONS / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    for name in ("favicon-32.png", "apple-touch-icon.png", "favicon.ico", "og-default.png"):
        path = ICONS / name
        print(f"{name}: {path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
