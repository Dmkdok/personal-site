"""F63 / ADR-035 — a video in an article is a facade the reader opts into.

The claim being proved here is a negative one, and it is the reason the facade
exists: a published page carrying a video contains **no `<iframe>`** and makes
**no request to the video host** until the reader presses play. Both halves are
watched rather than inferred — the requests through Playwright's own network
events, the markup through the DOM.

The press is asserted by the `<iframe>` that replaces the button and by where the
caret lands (F-002). Whether the video host then answers is not asserted: that
would make this test depend on somebody else's uptime, and it is not the property
under test.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.conftest import Trash
from e2e.helpers import AdminApi, photo_bytes, ru

YOUTUBE_ID = "dQw4w9WgXcQ"
EMBED = f"https://www.youtube.com/embed/{YOUTUBE_ID}?autoplay=1"

#: Every host the three supported services could be reached at, so a request to
#: any of them fails this test rather than only the one we happen to embed.
VIDEO_HOSTS = ("youtube.com", "youtu.be", "ytimg.com", "googlevideo.com", "rutube.ru", "vk.com")


def _third_party(urls: list[str]) -> list[str]:
    return [url for url in urls if any(host in url for host in VIDEO_HOSTS)]


def test_a_published_video_asks_the_host_for_nothing_until_the_press(
    page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    post = trash.post(admin_api.create_post(f"E2E видео {run_token}"))
    admin_api.publish_post(post, body_md=f"Разбор съёмки\n\nhttps://youtu.be/{YOUTUBE_ID}\n")

    requested: list[str] = []
    page.on("request", lambda request: requested.append(request.url))

    page.goto(f"/blog/{post.slug}")

    # The visitor's page: a control, and nothing that loads.
    facade = page.locator(".prose-video__play")
    expect(facade).to_be_visible()
    assert page.locator("iframe").count() == 0, "the page shipped with a player in it"
    assert facade.get_attribute("data-video") == EMBED
    reached = _third_party(requested)
    assert not reached, f"the page reached the video host before the press: {reached}"

    facade.click()

    frame = page.locator("iframe.prose-video__frame")
    expect(frame).to_have_count(1)
    assert frame.get_attribute("src") == EMBED
    assert frame.get_attribute("title") == ru("prose.video_frame")
    expect(page.locator(".prose-video__play")).to_have_count(0)
    # F-002: the control the caret was on has left the document, and the caret
    # went to the thing that replaced it rather than to <body>.
    assert page.evaluate("() => document.activeElement.tagName.toLowerCase()") == "iframe"


def test_a_picture_from_our_own_media_is_the_poster(
    page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """And the poster is our own file — the service's thumbnail is never fetched."""
    post = trash.post(admin_api.create_post(f"E2E видео с постером {run_token}"))
    poster = admin_api.upload_inline_image(
        post, photo_bytes(1200, 675, seed=7), f"v-{run_token}.jpg"
    )
    admin_api.publish_post(post, body_md=f"[![Кадр]({poster})](https://youtu.be/{YOUTUBE_ID})\n")

    requested: list[str] = []
    page.on("request", lambda request: requested.append(request.url))

    page.goto(f"/blog/{post.slug}")

    poster_image = page.locator(".prose-video__play img")
    expect(poster_image).to_be_visible()
    assert (poster_image.get_attribute("src") or "").startswith("/media/")
    reached = _third_party(requested)
    assert not reached, f"the page reached the video host: {reached}"


def test_the_owner_sees_the_same_facade_in_the_editors_preview(
    admin_page: Page, admin_api: AdminApi, trash: Trash, run_token: str
) -> None:
    """F28: the preview and the page go through one `render_markdown`, and since
    T138 through one script too — a facade that did nothing in the preview would
    be the one thing there that does not behave like the published page."""
    post = trash.post(admin_api.create_post(f"E2E видео превью {run_token}"))

    admin_page.goto(f"/blog/{post.slug}/edit")
    admin_page.locator("#post-body").fill(f"https://youtu.be/{YOUTUBE_ID}\n")

    preview = admin_page.locator(".editor__preview .prose-video__play")
    expect(preview).to_be_visible()
    assert preview.get_attribute("data-video") == EMBED

    preview.click()
    expect(admin_page.locator(".editor__preview iframe.prose-video__frame")).to_have_count(1)
