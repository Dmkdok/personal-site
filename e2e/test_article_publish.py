"""Launch flow 3 — write and publish an article (SPEC F28, F30, F31; user flow 9)."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, ru

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
