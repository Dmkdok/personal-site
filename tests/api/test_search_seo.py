"""Site-wide search and the SEO endpoints."""

from datetime import UTC, datetime

import pytest

from app.models.album import Album
from app.models.post import Post, PostStatus
from app.models.project import Project


@pytest.fixture
def content(db):
    """One published and one hidden item of each kind, all mentioning «Эльбрус»."""
    made = [
        Post(
            slug="published-post",
            title="Восхождение на Эльбрус",
            excerpt="Ночёвка на пять тысяч триста",
            body_md="Текст",
            body_html="<p>Текст</p>",
            status=PostStatus.PUBLISHED,
            published_at=datetime.now(UTC),
        ),
        Post(
            slug="draft-post",
            title="Черновик про Эльбрус",
            excerpt="Ещё не готово",
            body_md="",
            body_html="",
            status=PostStatus.DRAFT,
        ),
        Project(
            slug="published-project",
            title="Трекер маршрутов Эльбрус",
            summary="Логистика горных походов",
            is_published=True,
        ),
        Project(
            slug="hidden-project",
            title="Скрытый Эльбрус",
            summary="Ещё не показываем",
            is_published=False,
        ),
        Album(slug="published-album", title="Эльбрус, западное плато", is_published=True),
        Album(slug="hidden-album", title="Эльбрус, черновой отбор", is_published=False),
    ]
    db.add_all(made)
    db.commit()
    yield made

    for item in made:
        db.delete(db.merge(item))
    db.commit()


def test_search_finds_published_content_across_sections(client, content):
    html = client.get("/search", params={"q": "Эльбрус"}).text

    assert "Восхождение на Эльбрус" in html
    assert "Трекер маршрутов Эльбрус" in html
    assert "Эльбрус, западное плато" in html


def test_search_hides_drafts_and_unpublished_from_visitors(client, content):
    html = client.get("/search", params={"q": "Эльбрус"}).text

    assert "Черновик про Эльбрус" not in html
    assert "Скрытый Эльбрус" not in html
    assert "Эльбрус, черновой отбор" not in html


def test_search_uses_russian_stemming(client, content):
    """A declined form must still match — this is why the tsvector uses 'russian'."""
    html = client.get("/search", params={"q": "эльбрусе"}).text
    assert "Восхождение на Эльбрус" in html


@pytest.mark.parametrize("query", ["", " ", "a", "   %  "])
def test_short_or_empty_queries_give_guidance_not_an_error(client, query):
    response = client.get("/search", params={"q": query})
    assert response.status_code == 200
    assert "Ничего не нашлось" not in response.text


def test_no_results_state(client, content):
    response = client.get("/search", params={"q": "заведомонесуществующееслово"})
    assert response.status_code == 200
    assert "Ничего не нашлось" in response.text


def test_robots_txt(client):
    body = client.get("/robots.txt").text
    assert "Disallow: /admin/" in body
    assert "Sitemap:" in body


def test_sitemap_lists_published_pages_only(client, content):
    body = client.get("/sitemap.xml").text

    assert "/blog/published-post" in body
    assert "/dev/published-project" in body
    assert "/photo/published-album" in body

    assert "draft-post" not in body
    assert "hidden-project" not in body
    assert "hidden-album" not in body


def test_every_public_page_has_title_and_canonical(client):
    for path in ("/", "/dev", "/photo", "/blog"):
        html = client.get(path).text
        assert "<title>" in html
        assert 'rel="canonical"' in html
        assert 'property="og:title"' in html
