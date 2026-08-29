"""The cabinet — F62 and F64, decided by ADR-029, ADR-036 and ADR-037.

Three private rooms that answer "what needs me", "how much is there" and "what is
in the storage", every answer linking back to the page that edits it. They author
nothing, and the only control in the whole cabinet is the retry
`_photo_tile.html` already posts to.

Several things are asserted here rather than in `e2e/test_me.py`, because they
need the database: the failed photograph, which cannot be arranged through the
upload route at all — a file that will not decode is refused with 422 before a row
exists, and every file that *does* decode gets at least one rendition by design
(`Profile.widths_for`) — the empty page, which needs to know that nothing is
waiting, and the photograph in flight, which settles too fast to catch through a
browser.
"""

import re
from pathlib import Path

import pytest

from app.models.album import Album
from app.models.photo import Photo, PhotoStatus
from app.models.post import Post, PostStatus
from app.models.project import Project

#: The three rooms and the one fragment behind «Проверить». Every one of them is
#: `/me`-prefixed, which is what makes `robots.txt`'s single `Disallow` enough.
ROOMS = ["/me", "/me/stats", "/me/media"]
ADDRESSES = [*ROOMS, "/me/media/orphans"]


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


def _figures(page: str) -> dict[str, str | int]:
    """«Сводка» as {name: value}, read out of its definition lists.

    Numbers come back as numbers so a test can assert a delta; «12,4 МБ» and a
    date stay strings.
    """
    pairs = re.findall(r"<dt[^>]*>\s*(.*?)\s*</dt>\s*<dd[^>]*>\s*(.*?)\s*</dd>", page, re.S)
    return {name: int(value) if value.isdigit() else value for name, value in pairs}


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
@pytest.mark.parametrize("address", ADDRESSES)
def test_the_address_does_not_exist_without_a_session(client, address):
    """404, not a redirect: a redirect to /login confirms the page is there.

    A draft article gets exactly this treatment. `test_authz_sweep.py`'s
    parametrized admin-read case asserts redirect-to-login semantics, which these
    routes deliberately do not have, so it is not extended to cover them — and
    nothing is added to any allow-list.

    Every address, not only `/me`: a room that answered 401 or 302 would confirm
    the cabinet exists, and the scan behind «Проверить» is an address too.
    """
    response = client.get(address, follow_redirects=False)
    assert response.status_code == 404, address


@pytest.mark.parametrize("room", ROOMS)
def test_the_owner_gets_every_room(admin_client, room):
    response = admin_client.get(room)
    assert response.status_code == 200, room
    assert "Кабинет" in response.text


@pytest.mark.parametrize("room", ROOMS)
def test_no_room_is_ever_indexed(admin_client, client, room):
    """One `Disallow` for three rooms — asserted to cover the prefix, per ADR-036.

    The line in `robots.txt` is `Disallow: /me`, and a prefix rule covers
    `/me/stats` and `/me/media` by being one. That is checked here rather than
    assumed, because it is the whole reason `seo.py` did not have to change.
    """
    assert 'content="noindex, nofollow"' in admin_client.get(room).text
    assert "Disallow: /me" in client.get("/robots.txt").text
    assert room.startswith("/me")
    assert "/me" not in client.get("/sitemap.xml").text


def test_the_rooms_name_each_other_and_mark_the_one_being_read(admin_client):
    """A menu of links, and `aria-current` on the room the owner is in (F64).

    Marked in the markup rather than by colour alone: the accent goes with
    `forced-colors`, and a screen reader never saw it in the first place.
    """
    for room, label in (("/me", "События"), ("/me/stats", "Сводка"), ("/me/media", "Медиа")):
        page = admin_client.get(room).text
        assert 'aria-label="Разделы кабинета"' in page

        links = re.findall(r"<a[^>]*cabinet-nav__link[^>]*>\s*([^<]*?)\s*</a>", page)
        assert links == ["События", "Сводка", "Медиа", "Ссылки"], (room, links)

        current = re.findall(r'<a[^>]*aria-current="page"[^>]*>\s*([^<]*?)\s*</a>', page)
        assert current == [label], (room, current)


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


def test_a_photograph_with_no_description_is_not_in_the_cabinet(admin_client, db, hidden_album):
    """ADR-036: a missing description is a hint in the album, not a task here.

    On real data this section was two dozen rows all reading «Снимок в альбоме
    «X»», told apart only by where they lead — a list of non-problems on the page
    that lists problems. The prompt did not disappear with it: it stays on the
    album, in «Правка», where the owner is looking at the picture, and
    `test_photo.py::test_the_owner_is_told_how_many_photos_have_no_description`
    still asserts both the count line and `photo-item--undescribed` there.

    The failed photograph is asserted here too, because the cabinet dropping one
    list must not drop the other.
    """
    undescribed = _photo(db, hidden_album, status=PhotoStatus.READY)
    failed = _photo(db, hidden_album, status=PhotoStatus.FAILED)

    page = admin_client.get("/me").text

    assert f"#photo-{undescribed.id}" not in page
    assert "Снимки без описания" not in page
    assert f"#photo-{failed.id}" in page


def test_it_says_so_when_nothing_needs_attention(admin_client, db):
    """The branch that must not render blank.

    Asserts its own precondition: everything above cleans up after itself, so a
    failure here means something else left a row behind rather than that the
    page is wrong. Undescribed photographs are no longer counted here — they are
    no longer one of the things that make the page non-empty (ADR-036).
    """
    waiting = (
        db.query(Post).filter(Post.status == PostStatus.DRAFT).count()
        + db.query(Album).filter(Album.is_published.is_(False)).count()
        + db.query(Project).filter(Project.is_published.is_(False)).count()
        + db.query(Photo).filter(Photo.status == PhotoStatus.FAILED).count()
    )
    assert waiting == 0, f"{waiting} rows were left behind by another test"

    page = admin_client.get("/me").text
    assert "Ничего не ждёт" in page


# ------------------------------------------------------------------- «Сводка»
def test_the_summary_counts_what_is_there(admin_client, db, draft_post, hidden_album):
    """F64: counts over rows that already exist — no new model, no migration.

    Asserted as a delta rather than against an absolute, because the suite shares
    a database and every other test's rows are in these numbers too.
    """
    before = _figures(admin_client.get("/me/stats").text)

    extra_draft = Post(slug="me-stats-draft", title="Ещё черновик", status=PostStatus.DRAFT)
    db.add(extra_draft)
    db.commit()
    try:
        after = _figures(admin_client.get("/me/stats").text)
    finally:
        db.delete(db.get(Post, extra_draft.id))
        db.commit()

    assert after["Черновики статей"] == before["Черновики статей"] + 1
    assert after["Альбомы скрыты"] == before["Альбомы скрыты"]
    assert "Занято на диске" in after
    assert after["Занято на диске"].endswith("МБ")
    assert "Последняя статья" in after


def test_the_summary_names_every_photograph_status(admin_client):
    """All four, always — a status with nothing in it is information too."""
    figures = _figures(admin_client.get("/me/stats").text)
    for name in ("Ждут обработки", "Обрабатываются", "Готовы", "Не обработались"):
        assert name in figures, name


# --------------------------------------------------------------------- «Медиа»
def test_the_media_room_lists_photographs_in_flight_and_failed(admin_client, db, hidden_album):
    waiting = _photo(db, hidden_album, status=PhotoStatus.PROCESSING)
    failed = _photo(db, hidden_album, status=PhotoStatus.FAILED, error="не удалось прочитать")

    page = admin_client.get("/me/media").text

    assert "Снимки в обработке" in page
    assert f"#photo-{waiting.id}" in page
    assert f"#photo-{failed.id}" in page
    # The same endpoint the tile posts to — «Медиа» adds no second way in either.
    assert f'hx-post="/photo/admin/photos/{failed.id}/retry"' in page


def test_the_media_room_does_not_walk_the_disk_on_load(admin_client, monkeypatch):
    """ADR-037: the room that must stay usable when the storage is wrong.

    Proved by making the walk fail: `scan` raises, and the page still answers 200
    with the button on it. A room that walked on load would answer 500 here.

    `app.services.storage` is imported here rather than at the top of the file
    for the reason T136 recorded: a module-level import of a name a pre-change
    tree does not have makes the whole file fail *collection*, and a red run that
    is an ImportError proves nothing about the feature.
    """
    from app.services import storage

    def refuse(db):
        raise AssertionError("the disk was walked on page load")

    monkeypatch.setattr(storage, "scan", refuse)

    response = admin_client.get("/me/media")
    assert response.status_code == 200
    assert 'hx-get="/me/media/orphans"' in response.text
    assert "Файлов —" not in response.text


def test_the_scan_reports_orphans_and_offers_no_way_to_delete_them(admin_client, monkeypatch):
    """The fragment behind «Проверить» — a read, and the only thing on it.

    `scan` is replaced rather than arranged on disk: what is under test is what
    the room does with an answer, and the walk that produces one is verified by
    running `scripts/media_orphans.py` before and after the move (ADR-037).
    """
    from app.services import storage

    orphan = storage.Upload(stem="photos/1-album/deadbeef", files=[Path("gone.jpg")], owners=[])
    shared = storage.Upload(
        stem="photos/1-album/cafe",
        files=[Path("kept.jpg")],
        owners=["photo 7 (album 1)", "post 3 «Осень»"],
    )
    monkeypatch.setattr(storage, "scan", lambda db: storage.DiskScan(uploads=[orphan, shared]))
    monkeypatch.setattr(storage, "empty_directories", lambda: [])

    page = admin_client.get("/me/media/orphans").text

    assert "photos/1-album/deadbeef" in page
    assert "Ни на что не ссылаются — 1" in page
    assert "Одна загрузка на нескольких страницах — 1" in page
    assert "post 3 «Осень»" in page
    # Nothing in the cabinet deletes a file, and the page says where deleting is.
    assert "hx-delete" not in page
    assert "--prune" in page


def test_the_scan_says_so_when_nothing_is_orphaned(admin_client, monkeypatch):
    from app.services import storage

    monkeypatch.setattr(storage, "scan", lambda db: storage.DiskScan(uploads=[]))
    monkeypatch.setattr(storage, "empty_directories", lambda: [])

    page = admin_client.get("/me/media/orphans").text

    assert "Все файлы на что-то ссылаются" in page
    assert "Файлов — 0, загрузок — 0" in page


def test_the_password_is_stated_rather_than_offered(admin_client):
    """ADR-029: `ensure_admin_user` rewrites the hash at every start."""
    page = admin_client.get("/me").text
    assert "переменных окружения" in page
    assert 'type="password"' not in page
