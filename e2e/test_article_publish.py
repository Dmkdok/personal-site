"""Launch flow 3 — write and publish an article (SPEC F28, F30, F31; user flow 9)."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, csrf_of, photo_bytes, ru, switch_mode

BODY = """## Подзаголовок

Первый абзац статьи, написанный **жирным** и обычным текстом.

- пункт первый
- пункт второй
"""


@pytest.mark.launch_flow
def test_write_preview_and_publish_an_article(
    admin_page: Page, page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    title = f"E2E статья {run_token}"

    # -- draft created from /blog ----------------------------------------
    admin_page.goto("/blog")
    # «Новая статья» is an owner-only block, so it is off the page in «Просмотр»
    # since I5 (ADR-032). The owner enters «Правка» to write; so does this.
    switch_mode(admin_page, "edit")
    admin_page.get_by_role("button", name=ru("blog.new"), exact=True).click()
    admin_page.get_by_label(ru("blog.new_title_label")).fill(title)
    admin_page.get_by_role("button", name=ru("blog.new_submit")).click()

    # HX-Redirect drops the owner straight into the editor.
    expect(admin_page).to_have_url(re.compile(r"/blog/[^/]+/edit$"))
    post_id = int(admin_page.locator("#post-form").get_attribute("hx-post").rsplit("/", 1)[-1])
    trash.post_id(post_id)
    slug = admin_page.locator("#post-slug").input_value()

    # F30: a draft is invisible to a visitor.
    assert page.request.get(f"/blog/{slug}").status == 404

    # -- F28: preview renders through the published page's own pipeline ---
    admin_page.get_by_label(ru("blog.body_label")).fill(BODY)
    preview = admin_page.locator("#preview-body")
    expect(preview.get_by_role("heading", name="Подзаголовок")).to_be_visible(timeout=5000)
    expect(preview.get_by_role("listitem")).to_have_count(2)
    expect(preview.locator("strong")).to_have_text("жирным")

    # -- F31: raw HTML in the source is sanitised away --------------------
    admin_page.get_by_label(ru("blog.body_label")).fill(
        BODY
        + '\n<img src=x onerror="window.__pwned = true">\n<script>window.__pwned = true</script>\n'
    )
    expect(preview.get_by_role("heading", name="Подзаголовок")).to_be_visible(timeout=5000)
    assert admin_page.evaluate("() => window.__pwned === undefined") is True
    assert "onerror" not in preview.inner_html()

    admin_page.get_by_label(ru("blog.body_label")).fill(BODY)
    expect(preview.locator("strong")).to_have_text("жирным", timeout=5000)

    # -- F30: publish ------------------------------------------------------
    admin_page.get_by_role("button", name=ru("blog.publish"), exact=True).click()
    meta = admin_page.locator("#editor-meta")
    expect(meta).to_contain_text(ru("blog.status_published"))
    expect(meta.get_by_role("button", name=ru("blog.unpublish"))).to_be_visible()

    # -- the visitor's view ------------------------------------------------
    page.goto(f"/blog/{slug}")
    expect(page.get_by_role("heading", name=title, level=1)).to_be_visible()
    expect(page.get_by_role("heading", name="Подзаголовок", level=2)).to_be_visible()
    assert page.evaluate("() => window.__pwned === undefined") is True
    # F8: no tags, no reading time, no counters anywhere on the card.
    page.goto("/blog")
    card = page.get_by_role("link", name=title)
    expect(card).to_have_count(1)
    assert "мин" not in card.inner_text()

    # F30 in reverse: back to a draft, and the URL closes again.
    admin_page.get_by_role("button", name=ru("blog.unpublish"), exact=True).click()
    expect(admin_page.locator("#editor-meta")).to_contain_text(ru("blog.status_draft"))
    assert page.request.get(f"/blog/{slug}").status == 404


# --------------------------------------------------------------------------
# F9: a picture the owner sized in Markdown, as the visitor gets it.
# --------------------------------------------------------------------------
PICTURE_BODY = """Обычная, по ширине текста:

![Вид с перевала]({url} "Рассвет над хребтом")

Шире текста:

![Вид с перевала]({url}){{.wide}}

Во всю колонку:

![Вид с перевала]({url}){{.full}}
"""


def _figure_widths(page: Page) -> dict[str, float]:
    """Rendered width of each figure, plus the text column it is measured against."""
    return page.evaluate(
        """() => {
          const width = (sel) => {
            const el = document.querySelector(sel);
            return el ? el.getBoundingClientRect().width : -1;
          };
          return {
            prose: width('.prose'),
            normal: width('.prose-figure:not([class*="--"])'),
            wide: width('.prose-figure--wide'),
            full: width('.prose-figure--full'),
            page: document.documentElement.clientWidth,
            scroll: document.documentElement.scrollWidth,
          };
        }"""
    )


def test_a_sized_picture_reaches_the_visitor(
    admin_page: Page, page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    # A real upload, so the renditions srcset points at are really on disk.
    admin_page.goto("/blog")
    upload = admin_page.request.post(
        "/blog/admin/images",
        multipart={
            "file": {
                "name": f"e2e-{run_token}.jpg",
                "mimeType": "image/jpeg",
                "buffer": photo_bytes(),
            }
        },
        headers={"X-CSRF-Token": csrf_of(admin_page)},
    )
    assert upload.status == 200, f"inline upload → {upload.status}: {upload.text()[:300]}"
    url = upload.json()["url"]

    post = trash.post(admin_api.create_post(f"E2E картинки {run_token}"))
    admin_api.publish_post(post, body_md=PICTURE_BODY.format(url=url))

    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"/blog/{post.slug}")

    # -- the markup ---------------------------------------------------------
    figures = page.locator(".prose figure")
    expect(figures).to_have_count(3)
    expect(page.locator(".prose-figure--wide")).to_have_count(1)
    expect(page.locator(".prose-figure--full")).to_have_count(1)

    # Only the first picture carried a title, so only it has a caption.
    captions = page.locator(".prose figcaption")
    expect(captions).to_have_count(1)
    expect(captions).to_have_text("Рассвет над хребтом")

    first = page.locator(".prose figure img").first
    expect(first).to_have_attribute("loading", "lazy")
    expect(first).to_have_attribute("decoding", "async")
    expect(first).to_have_attribute("alt", "Вид с перевала")
    # The `PROSE` ladder: 640 / 1280 / 1920, and no 2560 — a picture in a column
    # of text has nothing to do with what a photograph gets (ADR-014).
    srcset = first.get_attribute("srcset") or ""
    assert "640w" in srcset and "1920w" in srcset, f"thin srcset: {srcset!r}"

    # The picture is really served, not just referenced.
    assert page.request.get(url).status == 200

    # -- the geometry, at 1440 ---------------------------------------------
    wide = _figure_widths(page)
    assert wide["normal"] == pytest.approx(wide["prose"], abs=1), wide
    assert wide["wide"] > wide["normal"] + 40, wide
    assert wide["full"] > wide["wide"] + 40, wide
    assert wide["full"] <= wide["page"], f"the full width overflows the viewport: {wide}"
    assert wide["scroll"] <= wide["page"] + 1, f"the page scrolls sideways: {wide}"

    # Symmetric breakout: equal air on both sides of the widest figure.
    box = page.locator(".prose-figure--full").bounding_box()
    assert box is not None
    left, right = box["x"], wide["page"] - (box["x"] + box["width"])
    assert abs(left - right) <= 1, f"the breakout is lopsided: {left} vs {right}"

    # -- and at 360, where there is nothing left to break out of -----------
    page.set_viewport_size({"width": 360, "height": 780})
    narrow = _figure_widths(page)
    assert narrow["normal"] == pytest.approx(narrow["wide"], abs=1), narrow
    assert narrow["wide"] == pytest.approx(narrow["full"], abs=1), narrow
    assert narrow["scroll"] <= narrow["page"] + 1, f"the page scrolls sideways: {narrow}"


# --------------------------------------------------------------------------
# F47 — a cover is a cover, not the first picture in the article
# --------------------------------------------------------------------------
def test_the_cover_shows_on_the_card_and_in_og_but_not_in_the_article(
    admin_page: Page, page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """Both halves matter.

    Removing the picture from the body is easy; keeping it where it earns its
    place is the part a regression would quietly undo, and `og:image` has no
    other coverage — nothing else on the site reads `post.cover_path` for a
    link preview.
    """
    post = trash.post(admin_api.create_post(f"E2E обложка {run_token}"))

    # `csrf_of` reads the token out of the page the tab is on, so it has to be
    # on one.
    admin_page.goto("/blog")
    upload = admin_page.request.post(
        f"/blog/admin/posts/{post.id}/cover",
        multipart={
            "file": {
                "name": f"cover-{run_token}.jpg",
                "mimeType": "image/jpeg",
                "buffer": photo_bytes(seed=11),
            }
        },
        headers={"X-CSRF-Token": csrf_of(admin_page)},
    )
    assert upload.status == 200, f"cover upload → {upload.status}: {upload.text()[:300]}"

    admin_api.publish_post(post, body_md="Текст статьи без единой картинки.\n")

    # -- the article itself: no cover in the body -------------------------
    page.goto(f"/blog/{post.slug}")
    expect(page.locator("article img")).to_have_count(0)

    # -- but it is still the link preview ---------------------------------
    og_image = page.locator('meta[property="og:image"]').get_attribute("content")
    assert og_image, "the article lost its og:image with the cover"
    assert page.request.get(og_image).status == 200, f"og:image 404s: {og_image}"

    # -- and still the card on the index -----------------------------------
    page.goto("/blog")
    card_image = page.get_by_role("link", name=post.title).locator("img")
    expect(card_image).to_have_count(1)
    assert (card_image.get_attribute("src") or "") in og_image
