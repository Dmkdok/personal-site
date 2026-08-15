"""Site-wide search and the SEO endpoints."""

import re
from datetime import UTC, datetime

import pytest

from app.models.album import Album
from app.models.post import Post, PostStatus
from app.models.project import Project
from app.routers.search import MAX_GROUP_LIMIT
from app.services.search import DEFAULT_LIMIT


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
            body_md="Длинное описание",
            body_html="<p>Длинное описание</p>",
            is_published=True,
        ),
        Project(
            slug="cardonly-project",
            title="Только карточка про Эльбрус",
            summary="Ссылка ведёт прямо в репозиторий",
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


def test_a_capped_group_states_the_real_total_and_offers_the_rest(client, db):
    """UI-AUDIT F-014: the list stopped at twelve without saying so.

    «12 из 12» and «12 из 27» look the same when the page says neither, and a
    visitor cannot tell a complete answer from a truncated one.
    """
    total = DEFAULT_LIMIT + 5
    made = [
        Post(
            slug=f"counted-{index}",
            title=f"Счётная запись {index} про Эльбрус",
            excerpt="Текст",
            body_md="Текст",
            body_html="<p>Текст</p>",
            status=PostStatus.PUBLISHED,
            published_at=datetime.now(UTC),
        )
        for index in range(total)
    ]
    db.add_all(made)
    db.commit()

    try:
        html = client.get("/search", params={"q": "Эльбрус"}).text

        assert f"{DEFAULT_LIMIT} из {total}" in html
        assert f"Найдено: {total}" in html
        assert 'role="status"' in html
        assert "Показать ещё" in html

        # And the continuation is the server's, not the client's: it comes back
        # as the whole group, with the count and the button re-rendered from the
        # same query as the list.
        more = client.get(
            "/search/group",
            params={"q": "Эльбрус", "kind": "post", "limit": DEFAULT_LIMIT + 12},
        )
        assert more.status_code == 200
        assert f"{total} из {total}" in more.text
        assert "Показать ещё" not in more.text
        assert more.text.count('class="result"') == total

        assert client.get("/search/group", params={"q": "Эльбрус", "kind": "x"}).status_code == 404
    finally:
        for item in made:
            db.delete(db.merge(item))
        db.commit()


def test_the_continuation_says_where_the_caret_should_land(client, db):
    """«Показать ещё» sits inside the element it replaces, so it deletes itself.

    Three attributes decide where the caret goes next, and a visitor driving the
    site from the keyboard notices immediately if any of them is missing: the
    button's `id`, which is the only thing htmx can restore focus by; the
    section's `tabindex`, which makes it a place focus can be put at all; and
    `data-autofocus`, which `ui.js` honours on a swapped fragment — emitted only
    by the continuation, and only once the button is gone. On the page itself no
    group may claim the caret, or landing on `/search` would move it.
    """
    total = DEFAULT_LIMIT + 5
    made = [
        Post(
            slug=f"caret-{index}",
            title=f"Каретная запись {index} про Эльбрус",
            excerpt="Текст",
            body_md="Текст",
            body_html="<p>Текст</p>",
            status=PostStatus.PUBLISHED,
            published_at=datetime.now(UTC),
        )
        for index in range(total)
    ]
    db.add_all(made)
    db.commit()

    try:
        page = client.get("/search", params={"q": "Эльбрус"}).text
        assert 'id="more-post"' in page
        # Named on the section itself: `<main>` carries a `tabindex="-1"` of its
        # own, so a bare substring here would pass with the attribute deleted.
        assert re.search(r'<section[^>]*id="results-post"[^>]*tabindex="-1"', page)
        assert "data-autofocus" not in page

        # Still capped: the button comes back, so htmx has an id to restore to.
        partial = client.get(
            "/search/group", params={"q": "Эльбрус", "kind": "post", "limit": DEFAULT_LIMIT + 2}
        ).text
        assert 'id="more-post"' in partial
        assert "data-autofocus" not in partial

        # Nothing left to ask for: the button is gone and the section takes over.
        exhausted = client.get(
            "/search/group", params={"q": "Эльбрус", "kind": "post", "limit": DEFAULT_LIMIT + 12}
        ).text
        assert "Показать ещё" not in exhausted
        assert "data-autofocus" in exhausted
    finally:
        for item in made:
            db.delete(db.merge(item))
        db.commit()


def test_the_continuation_hides_exactly_what_the_page_hides(client, content):
    """`/search/group` is a second door into the same query, and it is public.

    The page's own filter is tested above; this asserts the new route did not
    arrive with a different one. `limit` is pushed to the ceiling so nothing can
    hide behind the cap rather than behind the predicate.
    """
    for kind in ("post", "project", "album"):
        response = client.get(
            "/search/group", params={"q": "Эльбрус", "kind": kind, "limit": MAX_GROUP_LIMIT}
        )

        assert response.status_code == 200
        assert "Черновик про Эльбрус" not in response.text, kind
        assert "Скрытый Эльбрус" not in response.text, kind
        assert "Эльбрус, черновой отбор" not in response.text, kind


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

    # A published project with no long description has no page: `project_detail`
    # answers 404 for it, so listing it would advertise a dead URL.
    assert "cardonly-project" not in body
    assert client.get("/dev/cardonly-project").status_code == 404


def test_every_public_page_has_title_and_canonical(client):
    for path in ("/", "/dev", "/photo", "/blog"):
        html = client.get(path).text
        assert "<title>" in html
        assert 'rel="canonical"' in html
        assert 'property="og:title"' in html


def test_a_query_over_the_cap_gets_guidance_not_a_json_422(client):
    """It used to hit FastAPI's validator, which answers JSON to a browser."""
    response = client.get("/search", params={"q": "э" * 400})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Запрос длиннее" in response.text


def test_index_pages_carry_a_default_og_image(client):
    """A page with no picture of its own still previews as something."""
    for path in ("/", "/dev", "/photo", "/blog"):
        html = client.get(path).text
        assert 'property="og:image"' in html, path
        assert "og-default.png" in html, path


def test_an_article_without_a_cover_falls_back_to_the_default(client, content):
    html = client.get("/blog/published-post").text

    assert 'property="og:image"' in html
    assert "og-default.png" in html
