"""The blog module end to end: visibility, lifecycle, slugs and the editor.

Everything here goes through HTTP, because the module's guarantees — a draft
that does not exist for a visitor, a preview that cannot diverge from the page —
are properties of the responses, not of the model.
"""

import itertools
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from app.config import settings
from app.models.post import Post, PostStatus
from app.services.images import group_name, release
from app.services.markdown import render_markdown
from app.services.slugs import make_slug


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _remove_posts_made_here(db):
    """Delete whatever a test created, however it created it.

    Articles are made both directly and through the admin endpoints, which
    commit in the application's own session; comparing the ids before and after
    catches both without any bookkeeping in the tests.
    """
    before = set(db.scalars(select(Post.id)))
    yield

    db.rollback()
    query = select(Post)
    if before:
        query = query.where(Post.id.notin_(before))
    for post in db.scalars(query):
        db.delete(post)
    db.commit()


@pytest.fixture
def as_visitor(client):
    """Sign the shared client out again.

    `admin_client` is the same object as `client` with a session attached, so a
    test that needs both roles has to drop the cookie rather than ask for both
    fixtures and quietly get one authenticated client twice.
    """

    def sign_out():
        client.cookies.clear()
        return client

    return sign_out


@pytest.fixture
def make_post(db):
    """An article written straight into the database."""

    def make(
        *,
        slug: str,
        title: str = "Заголовок",
        body_md: str = "Текст статьи.",
        excerpt: str = "",
        published: bool = True,
        published_at: datetime | None = None,
        cover_path: str | None = None,
        body_html: str | None = None,
    ) -> Post:
        post = Post(
            slug=slug,
            title=title,
            excerpt=excerpt,
            body_md=body_md,
            body_html=render_markdown(body_md) if body_html is None else body_html,
            cover_path=cover_path,
            status=PostStatus.PUBLISHED if published else PostStatus.DRAFT,
            published_at=(published_at or datetime.now(UTC)) if published else None,
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post

    return make


_DISTINCT = itertools.count(1)


def png_bytes(size: tuple[int, int] = (1800, 1200), *, seed: int | None = None) -> bytes:
    """Wide enough that both the 640 and the 1600 rendition are produced.

    Every call differs by one pixel unless `seed` says otherwise: identical
    bytes are stored once (F42), so a shared frame would put one test's cover in
    another test's directory, under whatever ladder that one asked for. Pass a
    fixed `seed` when deduplication is what is being tested.
    """
    image = Image.new("RGB", size, (38, 52, 70))
    mark = next(_DISTINCT) if seed is None else seed
    image.putpixel((0, 0), (mark % 251, (mark // 251) % 251, 17))

    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def renditions_on_disk():
    """Put real `<stem>_<width>.webp` files under the media root, then remove them.

    Needed because the card's `srcset` is built by globbing what exists rather
    than by naming widths: a fabricated `cover_path` with nothing behind it now
    honestly offers no alternatives.
    """
    written: list[Path] = []

    def place(stem: str, *widths: int) -> str:
        for width in widths:
            path = settings.derived_dir / f"{stem}_{width}.webp"
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (width, round(width * 2 / 3)), (70, 52, 38)).save(path, "WEBP")
            written.append(path)
        return f"{stem}_{max(widths)}.webp"

    yield place

    for path in written:
        path.unlink(missing_ok=True)


def create_draft(client, db, title: str) -> Post:
    """Use the real «Новая статья» flow and hand back the row it made."""
    response = client.post("/blog/admin/posts", data={"title": title})
    assert response.status_code == 204, response.text

    redirect = response.headers["HX-Redirect"]
    assert redirect.startswith("/blog/") and redirect.endswith("/edit")
    slug = redirect[len("/blog/") : -len("/edit")]

    db.expire_all()
    post = db.scalar(select(Post).where(Post.slug == slug))
    assert post is not None
    return post


def fields(post: Post, **overrides) -> dict[str, str]:
    """The editor form, as the browser would send it."""
    values = {
        "title": post.title,
        "slug": post.slug,
        "excerpt": post.excerpt,
        "body_md": post.body_md,
    }
    values.update(overrides)
    return values


# --------------------------------------------------------------------------
# F8 — the index
# --------------------------------------------------------------------------
def test_index_lists_published_articles_newest_first(client, make_post):
    now = datetime.now(UTC)
    make_post(slug="older-post", title="Ранняя запись", published_at=now - timedelta(days=3))
    make_post(slug="newer-post", title="Поздняя запись", published_at=now)

    html = client.get("/blog").text

    assert html.index("/blog/newer-post") < html.index("/blog/older-post")


def test_index_card_shows_cover_title_excerpt_and_date(client, make_post, renditions_on_disk):
    renditions_on_disk("posts/7-statia/abc", 640, 1600)
    make_post(
        slug="card-post",
        title="Ночёвка на плато",
        excerpt="Как мы ставили палатку в темноте.",
        published_at=datetime(2026, 8, 4, tzinfo=UTC),
        cover_path="posts/7-statia/abc_1600.webp",
    )

    html = client.get("/blog").text

    assert "Ночёвка на плато" in html
    assert "Как мы ставили палатку в темноте." in html
    assert "4 августа 2026" in html
    assert 'datetime="2026-08-04"' in html
    assert "/media/posts/7-statia/abc_1600.webp" in html
    # The narrower rendition is offered too, and it is offered because it is on
    # disk: the card globs for siblings rather than assuming a ladder, so a
    # cover deduplicated onto another profile's files still advertises the truth.
    assert "/media/posts/7-statia/abc_640.webp" in html


def test_a_card_offers_no_srcset_when_there_is_only_one_rendition(
    client, make_post, renditions_on_disk
):
    """The other half of the same rule: one rendition is not a choice."""
    renditions_on_disk("posts/8-odna/solo", 900)
    make_post(slug="solo-cover", title="Одна ширина", cover_path="posts/8-odna/solo_900.webp")

    html = client.get("/blog").text

    assert "/media/posts/8-odna/solo_900.webp" in html
    # Not an empty attribute — none at all. The card is the only picture on the
    # page, so nothing else can be supplying one.
    assert "srcset" not in html


def test_index_carries_no_tags_reading_time_or_counters(client, make_post):
    """An explicit requirement from the brief, not an oversight."""
    make_post(slug="bare-card", title="Без украшений")

    html = client.get("/blog").text.lower()

    for marker in ("reading-time", "read-time", "мин чтения", "просмотр", "views", "tag-list"):
        assert marker not in html, f"the index grew a {marker}"


def test_index_hides_drafts_from_visitors(client, make_post):
    make_post(slug="hidden-draft", title="Тайная запись", published=False)

    html = client.get("/blog").text

    assert "Тайная запись" not in html
    assert "Черновики" not in html


def test_index_shows_drafts_to_the_owner(admin_client, make_post):
    make_post(slug="owner-draft", title="Моя заготовка", published=False)

    html = admin_client.get("/blog").text

    assert "Моя заготовка" in html
    assert "Черновики" in html


def test_index_offers_no_admin_markup_to_a_visitor(client, make_post):
    make_post(slug="public-post", title="Открытая запись")

    html = client.get("/blog").text

    assert "/blog/admin/" not in html
    assert "Новая статья" not in html


# --------------------------------------------------------------------------
# F9, F30 — the article page and draft visibility
# --------------------------------------------------------------------------
def test_draft_is_404_for_an_anonymous_visitor(client, make_post):
    make_post(slug="secret-draft", title="Черновик", published=False)

    assert client.get("/blog/secret-draft").status_code == 404


def test_draft_is_visible_to_the_owner_and_marked_as_one(admin_client, make_post):
    make_post(slug="visible-draft", title="Черновик", published=False)

    response = admin_client.get("/blog/visible-draft")

    assert response.status_code == 200
    assert "Черновик. Эту страницу видите только вы." in response.text
    assert 'content="noindex' in response.text


def test_unknown_slug_is_404(client):
    assert client.get("/blog/ничего-такого-нет").status_code == 404


def test_article_renders_the_stored_html_inside_prose(client, make_post):
    post = make_post(
        slug="prose-post",
        title="Разметка",
        body_md="## Подзаголовок\n\nАбзац с **акцентом**.",
    )

    html = client.get(f"/blog/{post.slug}").text

    assert '<div class="prose">' in html
    assert "<h2>Подзаголовок</h2>" in html
    assert "<strong>акцентом</strong>" in html
    assert 'href="/static/css/prose.css' in html


def test_article_body_is_sanitised_on_the_way_in(admin_client, db):
    """F31 through the real write path, not just the renderer's unit test."""
    post = create_draft(admin_client, db, "Опасная статья")
    source = "Текст\n\n<script>alert('xss')</script>\n\n<img src=x onerror=alert(1)>"

    admin_client.post(f"/blog/admin/posts/{post.id}", data=fields(post, body_md=source))

    db.expire_all()
    stored = db.get(Post, post.id)
    assert "<script" not in stored.body_html
    assert "<img" not in stored.body_html

    html = admin_client.get(f"/blog/{stored.slug}").text
    assert "<script>alert" not in html


# --------------------------------------------------------------------------
# F30 — draft → published → draft
# --------------------------------------------------------------------------
def test_new_article_starts_as_an_invisible_draft(admin_client, as_visitor, db):
    post = create_draft(admin_client, db, "Свежая мысль")
    slug = post.slug

    assert post.status is PostStatus.DRAFT
    assert post.published_at is None
    assert as_visitor().get(f"/blog/{slug}").status_code == 404


def test_publishing_sets_the_date_and_opens_the_page(admin_client, as_visitor, db):
    post = create_draft(admin_client, db, "Пора публиковать")
    post_id = post.id

    response = admin_client.post(
        f"/blog/admin/posts/{post_id}/publish",
        data=fields(post, body_md="Готовый текст."),
    )
    assert response.status_code == 200

    db.expire_all()
    stored = db.get(Post, post_id)
    assert stored.status is PostStatus.PUBLISHED
    assert stored.published_at is not None
    slug = stored.slug

    visitor = as_visitor()
    assert visitor.get(f"/blog/{slug}").status_code == 200
    assert "Пора публиковать" in visitor.get("/blog").text


def test_unpublishing_hides_the_page_but_keeps_the_date(admin_client, as_visitor, db):
    post = create_draft(admin_client, db, "Туда и обратно")
    post_id = post.id
    admin_client.post(f"/blog/admin/posts/{post_id}/publish", data=fields(post))

    db.expire_all()
    published_at = db.get(Post, post_id).published_at

    admin_client.post(f"/blog/admin/posts/{post_id}/unpublish", data=fields(post))

    db.expire_all()
    stored = db.get(Post, post_id)
    assert stored.status is PostStatus.DRAFT
    # Republishing must restore the original date, not pretend the piece is new.
    assert stored.published_at == published_at
    assert as_visitor().get(f"/blog/{stored.slug}").status_code == 404


def test_saving_keeps_the_typed_text_and_reports_the_time(admin_client, db):
    post = create_draft(admin_client, db, "Черновик на сохранение")

    response = admin_client.post(
        f"/blog/admin/posts/{post.id}",
        data=fields(post, body_md="Первая строка.\n\nВторая строка."),
    )

    assert response.status_code == 200
    assert "Сохранено в" in response.text

    db.expire_all()
    stored = db.get(Post, post.id)
    assert stored.body_md == "Первая строка.\n\nВторая строка."
    assert stored.excerpt.startswith("Первая строка.")


def test_deleting_removes_the_article(admin_client, db):
    post = create_draft(admin_client, db, "Лишняя запись")
    post_id = post.id

    response = admin_client.post(f"/blog/admin/posts/{post_id}/delete")

    assert response.status_code == 204
    assert response.headers["HX-Redirect"] == "/blog"

    db.expire_all()
    assert db.get(Post, post_id) is None


# --------------------------------------------------------------------------
# F32 — slugs
# --------------------------------------------------------------------------
def test_slug_is_transliterated_from_a_russian_title(admin_client, db):
    post = create_draft(admin_client, db, "Восхождение на Эльбрус")

    assert post.slug == "voskhozhdenie-na-elbrus"


def test_colliding_titles_get_distinct_slugs(admin_client, db):
    first = create_draft(admin_client, db, "Одинаковый заголовок")
    second = create_draft(admin_client, db, "Одинаковый заголовок")
    third = create_draft(admin_client, db, "Одинаковый заголовок")

    assert second.slug == f"{first.slug}-2"
    assert third.slug == f"{first.slug}-3"
    assert len({first.slug, second.slug, third.slug}) == 3


def test_renaming_a_published_article_keeps_its_url(admin_client, as_visitor, db):
    post = create_draft(admin_client, db, "Старое название")
    post_id = post.id
    admin_client.post(f"/blog/admin/posts/{post_id}/publish", data=fields(post))

    db.expire_all()
    original_slug = db.get(Post, post_id).slug

    admin_client.post(
        f"/blog/admin/posts/{post_id}",
        data=fields(post, title="Совершенно новое название", slug=original_slug),
    )

    db.expire_all()
    assert db.get(Post, post_id).slug == original_slug
    assert as_visitor().get(f"/blog/{original_slug}").status_code == 200


def test_clearing_the_address_rebuilds_it_from_the_title(admin_client, db):
    post = create_draft(admin_client, db, "Первое имя")
    post_id, original_slug = post.id, post.slug

    response = admin_client.post(
        f"/blog/admin/posts/{post_id}",
        data=fields(post, title="Другое имя", slug=""),
    )

    db.expire_all()
    stored = db.get(Post, post_id)
    assert stored.slug == make_slug("Другое имя")
    assert stored.slug != original_slug
    # The address bar has to follow, or a reload would land on a 404.
    assert response.headers["HX-Replace-Url"] == f"/blog/{stored.slug}/edit"


def test_an_empty_title_still_produces_a_usable_article(admin_client, db):
    post = create_draft(admin_client, db, "   ")

    assert post.title == "Без названия"
    assert post.slug


# --------------------------------------------------------------------------
# F28 — the editor and its preview
# --------------------------------------------------------------------------
def test_editor_requires_a_session(client, make_post):
    make_post(slug="guarded-post", title="Под замком")

    response = client.get("/blog/guarded-post/edit", follow_redirects=False)

    assert response.status_code in (303, 401, 403)


def test_editor_renders_the_source_the_toolbar_and_the_preview(admin_client, db):
    post = create_draft(admin_client, db, "В редакторе")
    admin_client.post(f"/blog/admin/posts/{post.id}", data=fields(post, body_md="## Раздел"))

    html = admin_client.get(f"/blog/{post.slug}/edit").text

    assert 'id="post-form"' in html
    assert 'id="post-body"' in html
    assert 'id="preview-body"' in html
    assert 'hx-post="/blog/admin/preview"' in html
    assert 'aria-label="Форматирование"' in html
    assert 'href="/static/js/editor.js' in html or "js/editor.js" in html
    # The preview starts out showing what is already stored.
    assert "<h2>Раздел</h2>" in html


def test_preview_matches_the_published_rendering_of_the_same_source(admin_client, db):
    source = (
        "## Подзаголовок\n"
        "\n"
        "Абзац с **акцентом**, `кодом` и [ссылкой](https://example.com).\n"
        "\n"
        "- один\n"
        "- два\n"
        "\n"
        "> Цитата\n"
    )
    post = create_draft(admin_client, db, "Сравнение")
    admin_client.post(f"/blog/admin/posts/{post.id}/publish", data=fields(post, body_md=source))

    preview = admin_client.post("/blog/admin/preview", data={"body_md": source})
    db.expire_all()
    page = admin_client.get(f"/blog/{db.get(Post, post.id).slug}")

    assert preview.status_code == 200
    assert preview.text.strip()
    # Byte-for-byte: the page embeds exactly what the preview showed (F28).
    assert preview.text.strip() in page.text


def test_preview_sanitises_the_same_way_the_page_does(admin_client):
    response = admin_client.post(
        "/blog/admin/preview", data={"body_md": "<script>alert(1)</script>"}
    )

    assert response.status_code == 200
    assert "<script" not in response.text


def test_preview_requires_a_session(client):
    response = client.post("/blog/admin/preview", data={"body_md": "текст"})

    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------
# F29 — images
# --------------------------------------------------------------------------
def test_inline_image_upload_returns_markdown_for_the_cursor(admin_client):
    response = admin_client.post(
        "/blog/admin/images", files={"file": ("вершина.png", png_bytes(), "image/png")}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["url"].startswith("/media/posts/")
    assert body["url"].endswith(".webp")
    assert body["markdown"] == f"![описание изображения]({body['url']})"


def test_inline_image_upload_rejects_a_non_image(admin_client):
    response = admin_client.post(
        "/blog/admin/images", files={"file": ("payload.txt", b"not an image", "text/plain")}
    )

    assert response.status_code == 400
    assert response.json()["error"]


def test_cover_can_be_uploaded_and_removed(admin_client, db):
    post = create_draft(admin_client, db, "Со обложкой")

    upload = admin_client.post(
        f"/blog/admin/posts/{post.id}/cover",
        files={"file": ("cover.png", png_bytes(), "image/png")},
    )
    assert upload.status_code == 200

    db.expire_all()
    stored = db.get(Post, post.id)
    assert stored.cover_path and stored.cover_path.endswith("_1600.webp")
    assert "/media/" in upload.text

    removal = admin_client.post(f"/blog/admin/posts/{post.id}/cover/remove")
    assert removal.status_code == 200

    db.expire_all()
    assert db.get(Post, post.id).cover_path is None


def test_cover_upload_rejects_a_non_image(admin_client, db):
    post = create_draft(admin_client, db, "Плохая обложка")

    response = admin_client.post(
        f"/blog/admin/posts/{post.id}/cover",
        files={"file": ("payload.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    db.expire_all()
    assert db.get(Post, post.id).cover_path is None


# --------------------------------------------------------------------------
# The «Новая статья» affordance
# --------------------------------------------------------------------------
def test_new_form_and_its_cancel_swap_the_same_element(admin_client):
    form = admin_client.get("/blog/admin/new")
    button = admin_client.get("/blog/admin/new/cancel")

    assert form.status_code == 200
    assert button.status_code == 200
    assert 'id="blog-new"' in form.text
    assert 'id="blog-new"' in button.text


@pytest.mark.parametrize("path", ["/blog/admin/new", "/blog/admin/new/cancel"])
def test_new_form_endpoints_require_a_session(client, path):
    response = client.get(path, follow_redirects=False)

    assert response.status_code in (303, 401, 403)


# --------------------------------------------------------------------------
# F41 / F42 — media lifecycle: stored once, deleted only when nobody uses it
# --------------------------------------------------------------------------
def files_under(post: Post) -> list[Path]:
    """Every file in this article's own media directory, originals and derived."""
    group = group_name(post.id, post.slug)
    found: list[Path] = []
    for root in (settings.originals_dir, settings.derived_dir):
        directory = root / "posts" / group
        if directory.is_dir():
            found += [path for path in directory.iterdir() if path.is_file()]
    return found


def upload_cover(client, post: Post, data: bytes):
    return client.post(
        f"/blog/admin/posts/{post.id}/cover", files={"file": ("frame.png", data, "image/png")}
    )


def upload_into_body(client, post: Post, data: bytes):
    return client.post(
        "/blog/admin/images",
        files={"file": ("frame.png", data, "image/png")},
        data={"post_id": str(post.id)},
    )


def test_the_same_frame_as_cover_and_in_the_body_is_stored_once(admin_client, db):
    """F42, in the shape the owner will meet it: one frame, two places."""
    post = create_draft(admin_client, db, "Один кадр дважды")
    frame = png_bytes(seed=4242)

    assert upload_cover(admin_client, post, frame).status_code == 200
    inline = upload_into_body(admin_client, post, frame)
    assert inline.status_code == 200

    db.expire_all()
    stored = db.get(Post, post.id)

    # Same URL from both routes, and one original behind it.
    assert inline.json()["url"] == f"/media/{stored.cover_path}"
    originals = [path for path in files_under(stored) if ".webp" not in path.name]
    assert len(originals) == 1, originals

    release(db, stored.cover_path)


def test_a_second_upload_of_known_bytes_writes_no_second_original(admin_client, db):
    """The dedup hit skips storage, and skips rendering only when it can.

    This test used to assert that a hit rendered *nothing*, which is what Phase
    6 run 2 found wrong: `COVER` is (640, 1600) and `PROSE` is (640, 1280, 1920)
    — neither is a subset of the other, so a frame used twice was being served
    the first use's ladder. What F42 promises is one stored file behind one URL,
    not that a rung the second use needs goes unrendered.
    """
    post = create_draft(admin_client, db, "Без второй обработки")
    frame = png_bytes(seed=4343)  # 1800×1200

    assert upload_cover(admin_client, post, frame).status_code == 200
    db.expire_all()
    before = sorted(path.name for path in files_under(db.get(Post, post.id)))
    assert [name for name in before if name.endswith(".webp")] == [
        name for name in before if name.endswith(("_640.webp", "_1600.webp"))
    ]

    assert upload_into_body(admin_client, post, frame).status_code == 200
    db.expire_all()
    stored = db.get(Post, post.id)
    after = sorted(path.name for path in files_under(stored))

    # One original. The bytes are not stored a second time (F42).
    assert [name for name in after if not name.endswith(".webp")] == [
        name for name in before if not name.endswith(".webp")
    ]
    # Nothing the cover was using disappeared…
    assert set(before) <= set(after)
    # …and prose's own rung was rendered onto the same stem rather than skipped.
    assert [name for name in after if name.endswith("_1280.webp")], after
    release(db, stored.cover_path)


def test_deleting_one_article_keeps_a_cover_the_other_still_uses(admin_client, client, db):
    """The failure this design exists to prevent (F41, ADR-013)."""
    frame = png_bytes(seed=5150)
    first = create_draft(admin_client, db, "Первая с общей обложкой")
    second = create_draft(admin_client, db, "Вторая с общей обложкой")

    assert upload_cover(admin_client, first, frame).status_code == 200
    assert upload_cover(admin_client, second, frame).status_code == 200

    db.expire_all()
    shared = db.get(Post, first.id).cover_path
    assert shared and db.get(Post, second.id).cover_path == shared

    assert admin_client.post(f"/blog/admin/posts/{first.id}/delete").status_code == 204

    db.expire_all()
    assert (settings.derived_dir / shared).is_file()
    client.cookies.clear()
    assert client.get(f"/media/{shared}").status_code == 200

    # And the other way round: with the last article gone, so is the file. A
    # deletion test that only proves nothing was deleted proves nothing.
    assert admin_client.post(f"/blog/admin/posts/{second.id}/delete").status_code == 204
    assert not (settings.derived_dir / shared).exists()


def test_deleting_an_article_removes_every_rendition_and_the_directory(admin_client, db):
    """Found by glob: no width is reconstructed, so none is missed."""
    post = create_draft(admin_client, db, "Со всеми размерами")
    assert upload_cover(admin_client, post, png_bytes(seed=5151)).status_code == 200

    db.expire_all()
    stored = db.get(Post, post.id)
    group = group_name(stored.id, stored.slug)
    written = files_under(stored)
    assert len(written) >= 3  # the original plus the 640 and 1600 renditions

    assert admin_client.post(f"/blog/admin/posts/{post.id}/delete").status_code == 204

    assert not any(path.exists() for path in written)
    for root in (settings.originals_dir, settings.derived_dir):
        assert not (root / "posts" / group).exists()


def test_a_picture_cut_from_the_text_is_released_on_save(admin_client, db):
    """F41 for in-article pictures (T092)."""
    post = create_draft(admin_client, db, "С картинкой в тексте")
    inline = upload_into_body(admin_client, post, png_bytes(seed=6060))
    url = inline.json()["url"]
    relative = url[len("/media/") :]

    saved = admin_client.post(
        f"/blog/admin/posts/{post.id}", data=fields(post, body_md=f"Текст.\n\n![вид]({url})\n")
    )
    assert saved.status_code == 200
    assert (settings.derived_dir / relative).is_file()

    db.expire_all()
    post = db.get(Post, post.id)
    assert (
        admin_client.post(
            f"/blog/admin/posts/{post.id}", data=fields(post, body_md="Текст без картинки.")
        ).status_code
        == 200
    )

    assert not (settings.derived_dir / relative).exists()


def test_a_picture_still_used_by_another_article_survives_the_cut(admin_client, db, make_post):
    """And the reference check reads `body_html`, not only `body_md`.

    The other article here holds the URL in its rendered HTML alone. That is the
    trap T083 recorded: `body_html` is written once, at save, and keeps its own
    copy of every `/media/…` URL, so a check that reads only the Markdown
    deletes pictures that are still on a published page.
    """
    post = create_draft(admin_client, db, "Отдаёт картинку")
    url = upload_into_body(admin_client, post, png_bytes(seed=6161)).json()["url"]
    relative = url[len("/media/") :]

    assert (
        admin_client.post(
            f"/blog/admin/posts/{post.id}", data=fields(post, body_md=f"![вид]({url})")
        ).status_code
        == 200
    )

    make_post(
        slug="tolko-v-html",
        title="Только в HTML",
        body_md="Текст без ссылки на файл.",
        body_html=f'<p><img src="{url}" alt="вид" /></p>',
    )

    db.expire_all()
    post = db.get(Post, post.id)
    assert (
        admin_client.post(
            f"/blog/admin/posts/{post.id}", data=fields(post, body_md="Уже без картинки.")
        ).status_code
        == 200
    )

    assert (settings.derived_dir / relative).is_file()
    release(db, relative)
