"""F63 / ADR-041 — a video in an article embeds directly.

The claim being proved here is the one the owner asked for: a published page
carrying a video contains a real `<iframe>` **immediately**, on load, and a
request to the video host is observed **at load**, not gated behind a click —
the opposite of ADR-035's facade, which this iteration retires. Both halves
are watched rather than inferred — the request through Playwright's own
network events, the markup through the DOM.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, photo_bytes, ru

YOUTUBE_ID = "dQw4w9WgXcQ"
EMBED = f"https://www.youtube.com/embed/{YOUTUBE_ID}"

#: Every host the three supported services could be reached at, so a request to
#: any of them fails this test rather than only the one we happen to embed.
VIDEO_HOSTS = ("youtube.com", "youtu.be", "ytimg.com", "googlevideo.com", "rutube.ru", "vk.com")


def _third_party(urls: list[str]) -> list[str]:
    return [url for url in urls if any(host in url for host in VIDEO_HOSTS)]


def test_a_published_video_embeds_immediately(
    page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    post = trash.post(admin_api.create_post(f"E2E видео {run_token}"))
    admin_api.publish_post(post, body_md=f"Разбор съёмки\n\nhttps://youtu.be/{YOUTUBE_ID}\n")

    requested: list[str] = []
    page.on("request", lambda request: requested.append(request.url))

    page.goto(f"/blog/{post.slug}")

    frame = page.locator("iframe.prose-video__frame")
    expect(frame).to_have_count(1)
    assert frame.get_attribute("src") == EMBED
    assert frame.get_attribute("title") == ru("prose.video_frame")
    reached = _third_party(requested)
    assert reached, "the video host was never asked for anything, on load"


def test_a_pictures_caption_survives_the_retired_poster(
    page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """The poster affordance is retired (ADR-041): the picture never renders,
    but its own alt text still reaches the page as the figure's caption."""
    post = trash.post(admin_api.create_post(f"E2E видео с постером {run_token}"))
    poster = admin_api.upload_inline_image(
        post, photo_bytes(1200, 675, seed=7), f"v-{run_token}.jpg"
    )
    admin_api.publish_post(post, body_md=f"[![Кадр]({poster})](https://youtu.be/{YOUTUBE_ID})\n")

    page.goto(f"/blog/{post.slug}")

    assert page.locator(".prose-video img").count() == 0, "the poster still rendered"
    expect(page.locator(".prose-video figcaption")).to_have_text("Кадр")


def test_the_owner_sees_the_same_embed_in_the_editors_preview(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """F28: the preview and the page go through one `render_markdown`, so the
    embed the owner sees while editing is the same one a reader gets."""
    post = trash.post(admin_api.create_post(f"E2E видео превью {run_token}"))

    admin_page.goto(f"/blog/{post.slug}/edit")
    admin_page.locator("#post-body").fill(f"https://youtu.be/{YOUTUBE_ID}\n")

    frame = admin_page.locator(".editor__preview iframe.prose-video__frame")
    expect(frame).to_have_count(1)
    assert frame.get_attribute("src") == EMBED
