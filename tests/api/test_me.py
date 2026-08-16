"""The cabinet at `/me` — F62, decided by ADR-029.

One private page that answers "what needs me", every answer linking back to the
page that edits it. It authors nothing, and the only control on it is the retry
`_photo_tile.html` already posts to.

Two things are asserted here rather than in `e2e/test_me.py`, because they need
the database: the failed photograph, which cannot be arranged through the upload
route at all — a file that will not decode is refused with 422 before a row
exists, and every file that *does* decode gets at least one rendition by design
(`Profile.widths_for`) — and the empty page, which needs to know that nothing is
waiting.
"""

import pytest

from app.models.album import Album
from app.models.photo import Photo, PhotoStatus
from app.models.post import Post, PostStatus
from app.models.project import Project


@pytest.fixture
def draft_post(db):
    made = Post(slug="me-draft", title="Черновик кабинета", status=PostStatus.DRAFT)
    db.add(made)
    db.commit()
    yield made
    db.delete(db.get(Post, made.id))
    db.commit()


@pytest.fixture
def hidden_album(db):
    made = Album(slug="me-album", title="Неопубликованный альбом", is_published=False)
    db.add(made)
    db.commit()
    yield made
    db.delete(db.get(Album, made.id))
    db.commit()


@pytest.fixture
def hidden_project(db):
    made = Project(slug="me-project", title="Неопубликованный проект", is_published=False)
    db.add(made)
    db.commit()
    yield made
    db.delete(db.get(Project, made.id))
    db.commit()


def _photo(db, album: Album, *, status: PhotoStatus, alt: str = "", error: str | None = None):
    made = Photo(
        album_id=album.id,
        original_path=f"me/{status.value}-{alt or 'none'}.jpg",
        alt=alt,
        status=status,
        error=error,
    )
    db.add(made)
    db.commit()
    return made


# ------------------------------------------------------------------ visibility
def test_the_address_does_not_exist_without_a_session(client):
    """404, not a redirect: a redirect to /login confirms the page is there.

    A draft article gets exactly this treatment. `test_authz_sweep.py`'s
    parametrized admin-read case asserts redirect-to-login semantics, which this
    route deliberately does not have, so it is not extended to cover it — and
    nothing is added to any allow-list.
    """
    response = client.get("/me", follow_redirects=False)
    assert response.status_code == 404


def test_the_owner_gets_the_page(admin_client):
    response = admin_client.get("/me")
    assert response.status_code == 200
    assert "Кабинет" in response.text


def test_the_page_is_never_indexed(admin_client, client):
    assert 'content="noindex, nofollow"' in admin_client.get("/me").text
    assert "Disallow: /me" in client.get("/robots.txt").text
    assert "/me" not in client.get("/sitemap.xml").text


# --------------------------------------------------------------- what it lists
def test_it_lists_the_three_kinds_of_unpublished_thing(
    admin_client, draft_post, hidden_album, hidden_project
):
    page = admin_client.get("/me").text

    assert draft_post.title in page
    assert f"/blog/{draft_post.slug}/edit" in page

    assert hidden_album.title in page
    assert f"/photo/{hidden_album.slug}" in page

    # The board, not `/dev/{slug}`: a project with no long description answers
    # 404 there even to the owner, and the board is where it is published.
    assert hidden_project.title in page
    assert f"/dev#project-{hidden_project.id}" in page


def test_a_failed_photograph_is_listed_with_the_retry_it_already_had(
    admin_client, db, hidden_album
):
    photo = _photo(db, hidden_album, status=PhotoStatus.FAILED, error="не удалось прочитать")

    page = admin_client.get("/me").text

    assert f"Снимок в альбоме «{hidden_album.title}»" in page
    assert "не удалось прочитать" in page
    # The same endpoint the tile posts to — the cabinet adds no second way in.
    assert f'hx-post="/photo/admin/photos/{photo.id}/retry"' in page


def test_a_photograph_with_no_description_is_listed_once_a_failed_one_is_not(
    admin_client, db, hidden_album
):
    """A photograph that never finished is one problem, not two."""
    described = _photo(db, hidden_album, status=PhotoStatus.READY, alt="описан")
    undescribed = _photo(db, hidden_album, status=PhotoStatus.READY)
    failed = _photo(db, hidden_album, status=PhotoStatus.FAILED)

    page = admin_client.get("/me").text

    assert f"#photo-{undescribed.id}" in page
    assert f"#photo-{described.id}" not in page
    # Present, but in the failed list only — never asked for a description too.
    assert page.count(f"#photo-{failed.id}") == 1


def test_it_says_so_when_nothing_needs_attention(admin_client, db):
    """The branch that must not render blank.

    Asserts its own precondition: everything above cleans up after itself, so a
    failure here means something else left a row behind rather than that the
    page is wrong.
    """
    waiting = (
        db.query(Post).filter(Post.status == PostStatus.DRAFT).count()
        + db.query(Album).filter(Album.is_published.is_(False)).count()
        + db.query(Project).filter(Project.is_published.is_(False)).count()
        + db.query(Photo).filter(Photo.status == PhotoStatus.FAILED).count()
        + db.query(Photo).filter(Photo.alt == "", Photo.status == PhotoStatus.READY).count()
    )
    assert waiting == 0, f"{waiting} rows were left behind by another test"

    page = admin_client.get("/me").text
    assert "Ничего не ждёт" in page


def test_the_password_is_stated_rather_than_offered(admin_client):
    """ADR-029: `ensure_admin_user` rewrites the hash at every start."""
    page = admin_client.get("/me").text
    assert "переменных окружения" in page
    assert 'type="password"' not in page
