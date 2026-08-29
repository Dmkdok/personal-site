"""Shared articles: reachable only by their own secret link (F67-F71).

The public route is exercised through HTTP because its guarantee — a missing
and a wrong token answer byte-for-byte identically — is a property of the
response, not of the model. The admin routes are exercised the same way
`test_blog.py` exercises the blog's own editor: through the real create/save/
delete flow, never by writing rows the routes themselves would never produce.
"""

import re

import pytest
from sqlalchemy import select

from app.models.shared_article import SharedArticle
from app.services.markdown import render_markdown

#: What legitimately varies between any two otherwise-identical pages: the
#: per-request CSP nonce, and the canonical/og:url echo of whichever address
#: was actually requested — neither says anything about the token itself.
_VARYING = re.compile(r'nonce="[^"]*"|/s/[^"\s]+')


def _normalized(html: str) -> str:
    return _VARYING.sub("X", html)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _remove_shared_articles_made_here(db):
    """Delete whatever a test created, however it created it."""
    before = set(db.scalars(select(SharedArticle.id)))
    yield

    db.rollback()
    query = select(SharedArticle)
    if before:
        query = query.where(SharedArticle.id.notin_(before))
    for article in db.scalars(query):
        db.delete(article)
    db.commit()


@pytest.fixture
def as_visitor(client):
    """Sign the shared client out again (see test_blog.py for why)."""

    def sign_out():
        client.cookies.clear()
        return client

    return sign_out


@pytest.fixture
def make_shared(db):
    """A shared article written straight into the database."""

    def make(*, title: str = "Заголовок", body_md: str = "Текст.") -> SharedArticle:
        article = SharedArticle(title=title, body_md=body_md, body_html=render_markdown(body_md))
        db.add(article)
        db.commit()
        db.refresh(article)
        return article

    return make


def create_shared(client, title: str) -> int:
    """Use the real «Создать» flow and hand back the id it made."""
    response = client.post("/me/shared", data={"title": title})
    assert response.status_code == 204, response.text

    redirect = response.headers["HX-Redirect"]
    assert redirect.startswith("/me/shared/") and redirect.endswith("/edit")
    return int(redirect[len("/me/shared/") : -len("/edit")])


# --------------------------------------------------------------------------
# F67 — the public link
# --------------------------------------------------------------------------
def test_valid_token_renders_the_article_through_the_markdown_pipeline(client, make_shared):
    article = make_shared(title="Личная страница", body_md="## Раздел\n\nАбзац с **акцентом**.")

    response = client.get(f"/s/{article.share_token}")

    assert response.status_code == 200
    assert "Личная страница" in response.text
    assert "<h2>Раздел</h2>" in response.text
    assert "<strong>акцентом</strong>" in response.text


def test_shared_article_carries_noindex_unconditionally(client, make_shared):
    article = make_shared()

    html = client.get(f"/s/{article.share_token}").text

    assert 'content="noindex"' in html


def test_missing_and_wrong_token_are_byte_identical_404s(client, make_shared):
    make_shared(title="Существует, но не по этому адресу")

    missing = client.get(f"/s/{'a' * 43}")
    wrong = client.get(f"/s/{'b' * 43}")

    assert missing.status_code == 404
    assert wrong.status_code == 404
    # Identical but for the per-request nonce and the requested address itself
    # echoed back in the canonical link — neither reveals which case this was.
    assert _normalized(missing.text) == _normalized(wrong.text)


def test_shared_article_body_is_sanitised(client, make_shared):
    article = make_shared(
        title="Опасная",
        body_md="Текст\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>",
    )

    html = client.get(f"/s/{article.share_token}").text

    assert "<script>" not in html
    assert "<img" not in html


def test_no_route_under_the_token_accepts_a_mutating_method(client, make_shared):
    """F68 belt: the structural sweep proves this too, since no such method is
    ever registered — this isolates that from the CSRF guard in front of every
    unsafe method by sending a valid token, the same way test_authz_sweep.py does.
    """
    article = make_shared()
    token = client.get("/").text.split('X-CSRF-Token": "')[1].split('"')[0]

    for method in ("POST", "PUT", "PATCH", "DELETE"):
        response = client.request(
            method, f"/s/{article.share_token}", headers={"X-CSRF-Token": token}
        )
        assert response.status_code == 405, (method, response.status_code)


# --------------------------------------------------------------------------
# F69 — invisible to discovery
# --------------------------------------------------------------------------
def test_shared_article_is_absent_from_the_sitemap_and_search(client, make_shared):
    article = make_shared(title="Уникальныйзаголовокстатьи")

    sitemap = client.get("/sitemap.xml").text
    assert article.share_token not in sitemap
    assert "/s/" not in sitemap

    # The query itself is always echoed back by the search page; what must be
    # absent is the article turning up as a result of it — a link to its own
    # secret address is the tell.
    results = client.get("/search", params={"q": "Уникальныйзаголовокстатьи"}).text
    assert f"/s/{article.share_token}" not in results


# --------------------------------------------------------------------------
# F68 — admin-only management
# --------------------------------------------------------------------------
def test_list_room_does_not_exist_for_a_visitor(client):
    assert client.get("/me/shared").status_code == 404


def test_editor_requires_a_session(client, make_shared):
    article = make_shared()

    response = client.get(f"/me/shared/{article.id}/edit", follow_redirects=False)

    assert response.status_code in (303, 401, 403)


def test_create_requires_a_session(client):
    response = client.post("/me/shared", data={"title": "Чужая статья"})

    assert response.status_code in (401, 403)


def test_preview_requires_a_session(client):
    response = client.post("/me/shared/preview", data={"body_md": "текст"})

    assert response.status_code in (401, 403)


def test_save_delete_and_regenerate_require_a_session(client, make_shared):
    article = make_shared()

    save = client.post(f"/me/shared/{article.id}/save", data={"title": "x", "body_md": "y"})
    assert save.status_code in (401, 403)
    assert client.post(f"/me/shared/{article.id}/regenerate").status_code in (401, 403)
    assert client.post(f"/me/shared/{article.id}/delete").status_code in (401, 403)


def test_editing_an_unknown_article_is_404_for_the_owner(admin_client):
    assert admin_client.get("/me/shared/999999/edit").status_code == 404


# --------------------------------------------------------------------------
# F70 — the cabinet room
# --------------------------------------------------------------------------
def test_list_shows_the_owners_articles(admin_client, make_shared):
    article = make_shared(title="В списке")

    html = admin_client.get("/me/shared").text

    assert "В списке" in html
    assert f"/me/shared/{article.id}/edit" in html


def test_creating_starts_an_empty_article_with_its_own_token(admin_client, db):
    article_id = create_shared(admin_client, "Новая общая статья")

    article = db.get(SharedArticle, article_id)
    assert article is not None
    assert article.title == "Новая общая статья"
    assert article.body_md == ""
    assert article.share_token


def test_an_empty_title_still_produces_a_usable_article(admin_client, db):
    article_id = create_shared(admin_client, "   ")

    assert db.get(SharedArticle, article_id).title == "Без названия"


def test_saving_stores_the_markdown_and_its_rendering(admin_client, db):
    article_id = create_shared(admin_client, "На сохранение")

    response = admin_client.post(
        f"/me/shared/{article_id}/save",
        data={"title": "На сохранение", "body_md": "Первая строка.\n\nВторая строка."},
    )

    assert response.status_code == 200
    assert "Сохранено в" in response.text

    db.expire_all()
    stored = db.get(SharedArticle, article_id)
    assert stored.body_md == "Первая строка.\n\nВторая строка."
    assert "<p>Первая строка.</p>" in stored.body_html


def test_preview_matches_the_published_rendering_of_the_same_source(admin_client, db):
    source = "## Подзаголовок\n\nАбзац с **акцентом** и [ссылкой](https://example.com).\n"
    article_id = create_shared(admin_client, "Сравнение")
    admin_client.post(
        f"/me/shared/{article_id}/save", data={"title": "Сравнение", "body_md": source}
    )

    preview = admin_client.post("/me/shared/preview", data={"body_md": source})
    db.expire_all()
    token = db.get(SharedArticle, article_id).share_token
    page = admin_client.get(f"/s/{token}")

    assert preview.status_code == 200
    assert preview.text.strip()
    # Byte-for-byte: the page embeds exactly what the preview showed (F67).
    assert preview.text.strip() in page.text


def test_preview_sanitises_the_same_way_the_page_does(admin_client):
    response = admin_client.post(
        "/me/shared/preview", data={"body_md": "<script>alert(1)</script>"}
    )

    assert response.status_code == 200
    assert "<script" not in response.text


def test_deleting_removes_the_article(admin_client, db):
    article_id = create_shared(admin_client, "Лишняя")

    response = admin_client.post(f"/me/shared/{article_id}/delete")

    assert response.status_code == 204
    assert response.headers["HX-Redirect"] == "/me/shared"
    db.expire_all()
    assert db.get(SharedArticle, article_id) is None


# --------------------------------------------------------------------------
# F71 — regenerating a token
# --------------------------------------------------------------------------
def test_regenerating_invalidates_the_old_link_and_issues_a_working_new_one(
    admin_client, as_visitor, db
):
    article_id = create_shared(admin_client, "Со сменой ссылки")
    db.expire_all()
    old_token = db.get(SharedArticle, article_id).share_token

    response = admin_client.post(f"/me/shared/{article_id}/regenerate")
    assert response.status_code == 200

    db.expire_all()
    new_token = db.get(SharedArticle, article_id).share_token
    assert new_token != old_token

    visitor = as_visitor()
    assert visitor.get(f"/s/{old_token}").status_code == 404
    assert visitor.get(f"/s/{new_token}").status_code == 200
