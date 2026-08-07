"""The blog module end to end: visibility, lifecycle, slugs and the editor.

Everything here goes through HTTP, because the module's guarantees — a draft
that does not exist for a visitor, a preview that cannot diverge from the page —
are properties of the responses, not of the model.
"""

from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import select

from app.models.post import Post, PostStatus
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
    ) -> Post:
        post = Post(
            slug=slug,
            title=title,
            excerpt=excerpt,
            body_md=body_md,
            body_html=render_markdown(body_md),
            cover_path=cover_path,
            status=PostStatus.PUBLISHED if published else PostStatus.DRAFT,
            published_at=(published_at or datetime.now(UTC)) if published else None,
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post

    return make


def png_bytes(size: tuple[int, int] = (1800, 1200)) -> bytes:
    """Wide enough that both the 640 and the 1600 rendition are produced."""
    buffer = BytesIO()
    Image.new("RGB", size, (38, 52, 70)).save(buffer, "PNG")
    return buffer.getvalue()


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


def test_index_card_shows_cover_title_excerpt_and_date(client, make_post):
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
    # The 640 rendition comes from the same store_and_process call, so the card
    # can offer it without a second database column.
    assert "/media/posts/7-statia/abc_640.webp" in html


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
