"""The photography module end to end: albums, uploads, visibility, deletion.

Test images are generated with Pillow at test time — no binary is committed.
Uploads are processed by the real background pool, so the tests wait for the
pipeline rather than reaching past it.
"""

import io
import itertools
import time

import pytest
from PIL import Image
from sqlalchemy import select

from app.config import settings
from app.models.album import Album
from app.models.photo import Photo, PhotoStatus
from app.routers.photos import recover_stuck_photos
from app.services import images

PROCESS_TIMEOUT = 30.0


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
_DISTINCT = itertools.count(1)


def make_jpeg(width: int = 1800, height: int = 1200, *, seed: int | None = None) -> bytes:
    """A gradient that differs from every other one unless `seed` says otherwise.

    Identical bytes are stored once (F42), so two tests sharing a frame would
    share a file — the second upload landing in the first album's directory and
    skipping the pipeline. Pass a fixed `seed` when that is the point of the test.
    """
    band = Image.linear_gradient("L")
    image = Image.merge("RGB", (band, band.transpose(Image.Transpose.ROTATE_90), band))
    image = image.resize((width, height), Image.Resampling.BILINEAR)
    mark = next(_DISTINCT) if seed is None else seed
    image.putpixel((0, 0), (mark % 251, (mark // 251) % 251, 17))

    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90)
    return buffer.getvalue()


def upload(client, album_id: int, data: bytes, filename: str, content_type: str):
    return client.post(
        f"/photo/admin/albums/{album_id}/photos",
        files={"file": (filename, data, content_type)},
    )


def settled(db, photo_id: int) -> Photo:
    """Wait for the background pool to finish with one photo."""
    deadline = time.monotonic() + PROCESS_TIMEOUT
    while time.monotonic() < deadline:
        db.rollback()  # a fresh snapshot; the pool commits from its own session
        photo = db.get(Photo, photo_id)
        if photo is not None and photo.status in (PhotoStatus.READY, PhotoStatus.FAILED):
            return photo
        time.sleep(0.1)
    raise AssertionError(f"photo {photo_id} never left the pipeline")


def files_of(photo: Photo) -> list:
    paths = [settings.originals_dir / photo.original_path]
    paths += [
        settings.derived_dir / relative
        for relative in (photo.thumb_path, photo.medium_path, photo.large_path)
        if relative
    ]
    return paths


def row_gone(db, model, pk: int) -> bool:
    """Ask the database whether a row survives, bypassing the identity map.

    `db.get(Model, pk)` cannot answer this: the session still holds the deleted
    instance, and refreshing it raises ObjectDeletedError instead of returning
    None. For the same reason the caller must capture the id before deleting.
    """
    db.rollback()
    return db.scalar(select(model).where(model.id == pk)) is None


def photos_in(db, album_id: int) -> list[Photo]:
    return list(db.scalars(select(Photo).where(Photo.album_id == album_id)))


def drop_album(db, album_id: int) -> None:
    """Remove an album and every file it owns, so tests cannot leak into each other."""
    db.rollback()
    for photo in photos_in(db, album_id):
        for path in files_of(photo):
            path.unlink(missing_ok=True)

    row = db.get(Album, album_id)
    if row is not None:
        row.cover_photo_id = None
        db.add(row)
        db.flush()
        db.delete(row)
    db.commit()


@pytest.fixture
def album(db):
    """A published album, removed with everything it owns afterwards."""
    made = Album(slug="test-album", title="Тестовый альбом", caption="Подпись", is_published=True)
    db.add(made)
    db.commit()
    yield made
    drop_album(db, made.id)


@pytest.fixture
def draft_album(db):
    made = Album(slug="test-draft-album", title="Черновой альбом", is_published=False)
    db.add(made)
    db.commit()
    yield made
    drop_album(db, made.id)


# --------------------------------------------------------------------------
# Public pages (F3, F4, F26)
# --------------------------------------------------------------------------
def test_index_lists_published_albums(client, album):
    html = client.get("/photo").text
    assert album.title in html
    assert album.caption in html


def test_index_hides_unpublished_albums_from_visitors(client, draft_album):
    assert draft_album.title not in client.get("/photo").text


def test_unpublished_album_is_404_for_a_visitor(client, draft_album):
    assert client.get(f"/photo/{draft_album.slug}").status_code == 404


def test_unpublished_album_is_visible_to_the_admin_with_a_draft_marker(admin_client, draft_album):
    response = admin_client.get(f"/photo/{draft_album.slug}")
    assert response.status_code == 200
    assert "Черновик" in response.text


def test_missing_album_is_404(client):
    assert client.get("/photo/no-such-album").status_code == 404


def test_an_empty_album_shows_an_empty_state(client, album):
    assert "В альбоме пока нет фотографий" in client.get(f"/photo/{album.slug}").text


def test_the_upload_zone_publishes_the_servers_own_limits(admin_client, album):
    """F24: the browser refuses what the server would, using the server's numbers.

    Two places disagreeing about the ceiling is exactly how the proxy came to
    cap request bodies at 30 MB while the application accepted 50. If this ever
    fails, the client is enforcing a limit nobody set.
    """
    page = admin_client.get(f"/photo/{album.slug}").text

    assert f'data-max-bytes="{settings.max_upload_bytes}"' in page
    for content_type in images.ALLOWED_CONTENT_TYPES:
        assert content_type in page


# --------------------------------------------------------------------------
# Album CRUD (F21)
# --------------------------------------------------------------------------
def test_admin_creates_an_album_with_a_transliterated_slug(admin_client, db):
    response = admin_client.post(
        "/photo/admin/albums", data={"title": "Эльбрус, сентябрь", "caption": "Съёмка"}
    )
    assert response.status_code == 200
    assert response.headers["HX-Redirect"].startswith("/photo/elbrus")

    slug = response.headers["HX-Redirect"].removeprefix("/photo/")
    made = db.scalar(select(Album).where(Album.slug == slug))
    assert made is not None
    assert made.is_published is False  # a new album is never public by accident

    drop_album(db, made.id)


def test_creating_an_album_without_a_title_is_rejected_in_place(admin_client):
    response = admin_client.post("/photo/admin/albums", data={"title": "  ", "caption": "x"})
    # A 200 carrying the form back: htmx does not swap error responses, and the
    # typed caption has to survive.
    assert response.status_code == 200
    assert "Введите название альбома." in response.text
    assert 'value="x"' in response.text or ">x<" in response.text


def test_admin_edits_title_and_caption_from_the_album_page(admin_client, db, album):
    response = admin_client.post(
        f"/photo/admin/albums/{album.id}",
        data={"title": "Новое название", "caption": "Новая подпись"},
    )
    assert response.status_code == 200
    assert "Новое название" in response.text

    db.rollback()
    assert db.get(Album, album.id).caption == "Новая подпись"


def test_publish_toggle_flips_visibility(admin_client, client, db, draft_album):
    admin_client.post(f"/photo/admin/albums/{draft_album.id}/publish")
    db.rollback()
    assert db.get(Album, draft_album.id).is_published is True
    assert client.get(f"/photo/{draft_album.slug}").status_code == 200

    admin_client.post(f"/photo/admin/albums/{draft_album.id}/publish")
    db.rollback()
    assert db.get(Album, draft_album.id).is_published is False


def test_albums_can_be_reordered(admin_client, db, album, draft_album):
    admin_client.post("/photo/admin/order", data={"order": f"{draft_album.id},{album.id}"})
    db.rollback()
    assert db.get(Album, draft_album.id).sort_order < db.get(Album, album.id).sort_order


# --------------------------------------------------------------------------
# Upload (F22, F23, F24)
# --------------------------------------------------------------------------
def test_upload_happy_path_produces_a_ready_photo_with_srcset(admin_client, db, album):
    response = upload(admin_client, album.id, make_jpeg(), "shot.jpg", "image/jpeg")
    assert response.status_code == 201

    photo = settled(db, response.json()["id"])
    assert photo.status is PhotoStatus.READY
    assert photo.error is None
    assert (photo.width, photo.height) == (1800, 1200)
    assert photo.thumb_path and photo.medium_path
    assert all(path.is_file() for path in files_of(photo))

    # The first ready photo becomes the cover, so the index card is never empty.
    db.rollback()
    assert db.get(Album, album.id).cover_photo_id == photo.id

    page = admin_client.get(f"/photo/{album.slug}").text
    assert 'srcset="' in page
    assert 'loading="lazy"' in page
    assert 'width="1800"' in page and 'height="1200"' in page


def test_a_visitor_only_sees_ready_photos(client, admin_client, db, album):
    response = upload(admin_client, album.id, make_jpeg(900, 600), "shot.jpg", "image/jpeg")
    photo = settled(db, response.json()["id"])
    assert photo.status is PhotoStatus.READY

    html = client.get(f"/photo/{album.slug}").text
    assert f'id="photo-{photo.id}"' in html
    # Nothing admin-only leaks to a visitor.
    assert "/photo/admin/" not in html


@pytest.mark.parametrize(
    "filename,content_type,payload",
    [
        ("notes.txt", "text/plain", b"not an image at all"),
        ("renamed.jpg", "image/jpeg", b"PK\x03\x04 actually a zip"),
        ("broken.jpg", "image/jpeg", b"\xff\xd8\xff" + b"\x9c\x1f" * 512),
    ],
)
def test_each_rejection_reports_its_own_reason(
    admin_client, db, album, filename, content_type, payload
):
    response = upload(admin_client, album.id, payload, filename, content_type)
    assert response.status_code == 422
    assert response.json()["detail"]

    db.rollback()
    assert photos_in(db, album.id) == []


def test_one_rejection_does_not_disturb_the_rest_of_the_batch(admin_client, db, album):
    bad = upload(admin_client, album.id, b"not an image", "notes.txt", "text/plain")
    good = upload(admin_client, album.id, make_jpeg(800, 600), "shot.jpg", "image/jpeg")

    assert bad.status_code == 422
    assert good.status_code == 201
    assert settled(db, good.json()["id"]).status is PhotoStatus.READY


def test_upload_without_a_file_is_rejected(admin_client, album):
    response = admin_client.post(f"/photo/admin/albums/{album.id}/photos", files={})
    assert response.status_code == 422


def test_a_visitor_cannot_upload(client, album):
    token = client.get("/").text.split('X-CSRF-Token": "')[1].split('"')[0]
    response = client.post(
        f"/photo/admin/albums/{album.id}/photos",
        files={"file": ("shot.jpg", make_jpeg(400, 300), "image/jpeg")},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 401


# --------------------------------------------------------------------------
# Photo management (F25)
# --------------------------------------------------------------------------
def test_deleting_a_photo_removes_its_files_from_disk(admin_client, db, album):
    response = upload(admin_client, album.id, make_jpeg(1000, 750), "shot.jpg", "image/jpeg")
    photo = settled(db, response.json()["id"])
    photo_id = photo.id
    paths = files_of(photo)
    assert all(path.is_file() for path in paths)

    assert admin_client.delete(f"/photo/admin/photos/{photo_id}").status_code == 200

    assert row_gone(db, Photo, photo_id)
    assert not any(path.exists() for path in paths), "orphan files left on the volume"


def test_deleting_an_album_removes_every_photo_file(admin_client, db):
    created = admin_client.post("/photo/admin/albums", data={"title": "На удаление"})
    slug = created.headers["HX-Redirect"].removeprefix("/photo/")
    made = db.scalar(select(Album).where(Album.slug == slug))
    album_id = made.id

    response = upload(admin_client, album_id, make_jpeg(900, 600), "shot.jpg", "image/jpeg")
    photo = settled(db, response.json()["id"])
    photo_id = photo.id
    paths = files_of(photo)

    deleted = admin_client.delete(f"/photo/admin/albums/{album_id}")
    assert deleted.status_code == 200
    assert deleted.headers["HX-Redirect"] == "/photo"

    assert row_gone(db, Album, album_id)
    assert row_gone(db, Photo, photo_id)
    assert not any(path.exists() for path in paths)


def test_alt_text_is_saved_and_rendered(admin_client, db, album):
    response = upload(admin_client, album.id, make_jpeg(800, 600), "shot.jpg", "image/jpeg")
    photo = settled(db, response.json()["id"])

    saved = admin_client.post(
        f"/photo/admin/photos/{photo.id}/alt", data={"alt": "Ледник на рассвете"}
    )
    assert saved.status_code == 200
    assert "Ледник на рассвете" in saved.text

    db.rollback()
    assert db.get(Photo, photo.id).alt == "Ледник на рассвете"


def test_cover_can_be_moved_to_another_photo(admin_client, db, album):
    first = settled(
        db, upload(admin_client, album.id, make_jpeg(800, 600), "a.jpg", "image/jpeg").json()["id"]
    )
    second = settled(
        db, upload(admin_client, album.id, make_jpeg(600, 800), "b.jpg", "image/jpeg").json()["id"]
    )

    db.rollback()
    assert db.get(Album, album.id).cover_photo_id == first.id

    assert admin_client.post(f"/photo/admin/photos/{second.id}/cover").status_code == 200
    db.rollback()
    assert db.get(Album, album.id).cover_photo_id == second.id


def test_photos_can_be_reordered_by_drag_and_by_button(admin_client, db, album):
    first = settled(
        db, upload(admin_client, album.id, make_jpeg(800, 600), "a.jpg", "image/jpeg").json()["id"]
    )
    second = settled(
        db, upload(admin_client, album.id, make_jpeg(800, 600), "b.jpg", "image/jpeg").json()["id"]
    )

    admin_client.post(
        f"/photo/admin/albums/{album.id}/photo-order", data={"order": f"{second.id},{first.id}"}
    )
    db.rollback()
    assert db.get(Photo, second.id).sort_order < db.get(Photo, first.id).sort_order

    # The keyboard route reaches the same place.
    admin_client.post(f"/photo/admin/photos/{first.id}/move", data={"direction": "up"})
    db.rollback()
    assert db.get(Photo, first.id).sort_order < db.get(Photo, second.id).sort_order


# --------------------------------------------------------------------------
# Processing resilience (F27)
# --------------------------------------------------------------------------
def test_the_grid_stops_polling_once_nothing_is_pending(admin_client, db, album):
    response = upload(admin_client, album.id, make_jpeg(800, 600), "shot.jpg", "image/jpeg")
    settled(db, response.json()["id"])

    grid = admin_client.get(f"/photo/admin/albums/{album.id}/grid").text
    assert "every 2s" not in grid


def test_a_restart_requeues_a_photo_left_pending(admin_client, db, album):
    response = upload(admin_client, album.id, make_jpeg(900, 600), "shot.jpg", "image/jpeg")
    photo = settled(db, response.json()["id"])

    # Exactly the state a container restart leaves behind.
    photo.status = PhotoStatus.PROCESSING
    photo.error = None
    db.add(photo)
    db.commit()

    recover_stuck_photos()

    assert settled(db, photo.id).status is PhotoStatus.READY


def test_a_restart_fails_a_photo_whose_original_is_gone(admin_client, db, album):
    response = upload(admin_client, album.id, make_jpeg(900, 600), "shot.jpg", "image/jpeg")
    photo = settled(db, response.json()["id"])

    (settings.originals_dir / photo.original_path).unlink()
    photo.status = PhotoStatus.PENDING
    db.add(photo)
    db.commit()

    recover_stuck_photos()

    db.rollback()
    failed = db.get(Photo, photo.id)
    assert failed.status is PhotoStatus.FAILED
    assert failed.error

    # And the owner is offered a way out rather than a dead tile.
    page = admin_client.get(f"/photo/{album.slug}").text
    assert "Повторить обработку" in page


def test_a_failed_photo_can_be_retried(admin_client, db, album):
    response = upload(admin_client, album.id, make_jpeg(900, 600), "shot.jpg", "image/jpeg")
    photo = settled(db, response.json()["id"])

    photo.status = PhotoStatus.FAILED
    photo.error = "было плохо"
    db.add(photo)
    db.commit()

    assert admin_client.post(f"/photo/admin/photos/{photo.id}/retry").status_code == 200
    assert settled(db, photo.id).status is PhotoStatus.READY


# --------------------------------------------------------------------------
# Absences the brief asks for
# --------------------------------------------------------------------------
def test_no_tags_reading_time_or_counters_anywhere(client, admin_client, db, album):
    response = upload(admin_client, album.id, make_jpeg(800, 600), "shot.jpg", "image/jpeg")
    settled(db, response.json()["id"])

    for html in (client.get("/photo").text, client.get(f"/photo/{album.slug}").text):
        for banned in ("Теги", "тег", "мин чтения", "просмотр", "фотографий:"):
            assert banned not in html


# --------------------------------------------------------------------------
# F41 / F42 — one file per frame, and it goes when nobody wants it
# --------------------------------------------------------------------------
def test_the_same_frame_uploaded_twice_is_stored_once(admin_client, db, album):
    frame = make_jpeg(seed=8801)

    first = settled(db, upload(admin_client, album.id, frame, "a.jpg", "image/jpeg").json()["id"])
    second_id = upload(admin_client, album.id, frame, "b.jpg", "image/jpeg").json()["id"]

    db.rollback()
    second = db.get(Photo, second_id)

    # No pipeline run at all for the second one: the renditions already exist,
    # so it is ready in the response rather than after a poll.
    assert second.status is PhotoStatus.READY
    assert second.original_path == first.original_path
    assert (second.thumb_path, second.large_path) == (first.thumb_path, first.large_path)
    assert all(path.is_file() for path in files_of(second))


def test_deleting_one_of_two_photos_sharing_a_file_keeps_the_file(admin_client, db, album):
    frame = make_jpeg(seed=8802)

    first = settled(db, upload(admin_client, album.id, frame, "a.jpg", "image/jpeg").json()["id"])
    second_id = upload(admin_client, album.id, frame, "b.jpg", "image/jpeg").json()["id"]

    assert admin_client.delete(f"/photo/admin/photos/{first.id}").status_code == 200

    db.rollback()
    second = db.get(Photo, second_id)
    assert all(path.is_file() for path in files_of(second))

    # And once the last row referring to them is gone, so are the files.
    doomed = files_of(second)
    assert admin_client.delete(f"/photo/admin/photos/{second_id}").status_code == 200
    assert not any(path.exists() for path in doomed)


def test_a_photo_is_rendered_at_its_own_width_too(admin_client, db, album):
    """ADR-014: the photography profile has to be able to show the frame as shot."""
    photo = settled(
        db,
        upload(admin_client, album.id, make_jpeg(1800, 1200), "shot.jpg", "image/jpeg").json()[
            "id"
        ],
    )

    assert photo.large_path.endswith("_1800.webp")
    with Image.open(settings.derived_dir / photo.large_path) as rendition:
        assert rendition.size == (1800, 1200)
