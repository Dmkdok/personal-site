"""The image pipeline: what it accepts, what it renders, what it refuses.

Every fixture image is generated with Pillow at test time — no binary ever
enters the repository.
"""

import io
from pathlib import Path

import pytest
from PIL import Image

from app.config import settings
from app.services import images
from app.templating import translate

KIND = "test-pipeline"


# --------------------------------------------------------------------------
# Building material
# --------------------------------------------------------------------------
def make_image(
    width: int,
    height: int,
    fmt: str = "JPEG",
    *,
    orientation: int | None = None,
) -> bytes:
    """A recognisable gradient, so a resize that goes wrong is visible."""
    band = Image.linear_gradient("L")
    image = Image.merge(
        "RGB", (band, band.transpose(Image.Transpose.ROTATE_90), band.point(lambda v: 255 - v))
    ).resize((width, height), Image.Resampling.BILINEAR)

    buffer = io.BytesIO()
    options: dict[str, object] = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation  # 274 = Orientation
        options["exif"] = exif.tobytes()
    image.save(buffer, fmt, **options)
    return buffer.getvalue()


@pytest.fixture
def pipeline(db):
    """Run the pipeline and clean every file it wrote, pass or fail.

    Torn down with `release` rather than `delete_files`, so the `media_asset`
    row goes with the files: two tests generating the same gradient produce the
    same bytes, and a row left behind would deduplicate the second onto files
    the first has already deleted.
    """
    written: list[str] = []

    def run(
        data: bytes,
        filename: str = "shot.jpg",
        content_type: str = "image/jpeg",
        profile: images.Profile = images.PHOTO,
    ):
        stored = images.store_and_process(
            db, data, filename, content_type, kind=KIND, profile=profile
        )
        db.commit()
        written.append(stored.original_path)
        written.extend(stored.derivatives.values())
        return stored

    yield run
    images.release(db, *written)


def derived(relative: str) -> Path:
    return settings.derived_dir / relative


def original(relative: str) -> Path:
    return settings.originals_dir / relative


def size_of(relative: str) -> tuple[int, int]:
    with Image.open(derived(relative)) as image:
        return image.size


# --------------------------------------------------------------------------
# Renditions (F23)
# --------------------------------------------------------------------------
def test_landscape_gets_every_target_width(pipeline):
    stored = pipeline(make_image(3000, 2000))

    # The ladder plus the source's own width: `PHOTO` is the profile that has to
    # be able to show the owner's frame at the size he prepared it (ADR-014).
    assert sorted(stored.derivatives) == [640, 1600, 2560, 3000]
    assert (stored.width, stored.height) == (3000, 2000)
    for width in (640, 1600, 2560):
        assert size_of(stored.derivatives[width]) == (width, round(2000 * width / 3000))
    assert size_of(stored.derivatives[3000]) == (3000, 2000)


def test_a_prose_picture_stops_at_1920(pipeline):
    """`PROSE` has no native rung: more pixels than 1920 buy nothing in a column."""
    stored = pipeline(make_image(3000, 2000), profile=images.PROSE)

    assert sorted(stored.derivatives) == [640, 1280, 1920]


def test_portrait_keeps_its_aspect_ratio(pipeline):
    stored = pipeline(make_image(1200, 1800))

    # 1600 and 2560 are wider than the original, so they are simply not made;
    # 1200 is the native rendition.
    assert sorted(stored.derivatives) == [640, 1200]
    assert (stored.width, stored.height) == (1200, 1800)
    assert size_of(stored.derivatives[640]) == (640, 960)
    assert size_of(stored.derivatives[1200]) == (1200, 1800)


def test_an_image_smaller_than_the_smallest_target_is_not_upscaled(pipeline):
    stored = pipeline(make_image(400, 300), profile=images.COVER)

    # There is still something servable, but it is the original size — never more.
    assert sorted(stored.derivatives) == [400]
    assert size_of(stored.derivatives[400]) == (400, 300)

    stem = stored.original_path.rsplit(".", 1)[0]
    assert not derived(f"{stem}_640.webp").exists()
    assert not derived(f"{stem}_1600.webp").exists()


def test_exif_orientation_is_applied_before_measuring(pipeline):
    """Orientation 6 means "rotate 90° clockwise to display"."""
    stored = pipeline(make_image(1000, 600, orientation=6))

    # Stored 1000×600, displayed 600×1000 — the recorded size is the displayed one.
    assert (stored.width, stored.height) == (600, 1000)
    assert size_of(stored.derivatives[600]) == (600, 1000)


def test_derivatives_are_webp(pipeline):
    stored = pipeline(make_image(1000, 800, "PNG"), filename="shot.png", content_type="image/png")

    for relative in stored.derivatives.values():
        assert relative.endswith(".webp")
        with Image.open(derived(relative)) as rendition:
            assert rendition.format == "WEBP"


def test_the_original_is_kept_byte_for_byte(pipeline):
    data = make_image(1200, 900)
    stored = pipeline(data)

    assert original(stored.original_path).read_bytes() == data
    assert stored.byte_size == len(data)


def test_the_stored_name_never_comes_from_the_client(pipeline):
    stored = pipeline(make_image(800, 600), filename="../../../etc/passwd.jpg")

    name = Path(stored.original_path).name
    assert "passwd" not in name
    assert ".." not in stored.original_path
    assert stored.original_path.startswith(f"{KIND}/")


# --------------------------------------------------------------------------
# Rejections (F24)
# --------------------------------------------------------------------------
def test_rejects_a_type_we_do_not_accept():
    data = make_image(400, 300, "GIF")
    with pytest.raises(images.ImageRejected):
        images.validate_upload("animation.gif", "image/gif", data)


def test_rejects_a_content_type_that_is_not_an_image():
    with pytest.raises(images.ImageRejected):
        images.validate_upload("notes.txt", "text/plain", b"just some text")


def test_rejects_a_file_over_the_size_cap():
    oversized = b"\xff\xd8\xff" + b"\x00" * settings.max_upload_bytes
    with pytest.raises(images.ImageRejected):
        images.validate_upload("huge.jpg", "image/jpeg", oversized)


def test_rejects_an_empty_file():
    with pytest.raises(images.ImageRejected):
        images.validate_upload("empty.jpg", "image/jpeg", b"")


def test_rejects_bytes_that_only_pretend_to_be_a_jpeg():
    """A renamed file passes the extension check and fails the magic-byte one."""
    with pytest.raises(images.ImageRejected):
        images.validate_upload("renamed.jpg", "image/jpeg", b"PK\x03\x04 this is a zip")


def test_rejects_a_corrupt_image_that_survives_validation(tmp_path):
    """Right magic bytes, unreadable content: only decoding catches this one."""
    corrupt = b"\xff\xd8\xff" + b"\x9c\x1f" * 512
    assert images.validate_upload("broken.jpg", "image/jpeg", corrupt) == "image/jpeg"

    path = tmp_path / "broken.jpg"
    path.write_bytes(corrupt)
    with pytest.raises(images.ImageRejected):
        images.verify_decodable(path)


def test_rejects_a_decompression_bomb(tmp_path, monkeypatch):
    """A valid image with an absurd pixel count is refused, not decoded.

    `DecompressionBombError` is not an `OSError` or a `ValueError`, so the
    narrow tuple this used to catch let it past `ImageRejected` entirely: the
    upload became a 500 with an HTML body, sent to a client parsing JSON, and
    the original stayed on disk.
    """
    monkeypatch.setattr(images, "MAX_PIXELS", 64)

    path = tmp_path / "bomb.png"
    Image.new("RGB", (64, 64), "white").save(path, "PNG")

    with pytest.raises(images.ImageRejected):
        images.verify_decodable(path)


def test_an_oversized_image_leaves_nothing_behind(db, monkeypatch):
    """Whatever the reason for rejection, the stored original goes with it."""
    monkeypatch.setattr(images, "MAX_PIXELS", 64)
    bucket = settings.originals_dir / KIND

    def files() -> set[Path]:
        return {path for path in bucket.rglob("*") if path.is_file()} if bucket.exists() else set()

    before = files()
    with pytest.raises(images.ImageRejected):
        images.store_and_process(db, make_image(200, 200), "big.jpg", "image/jpeg", kind=KIND)

    assert files() == before


def test_a_rejected_upload_leaves_nothing_behind(db):
    """The original is written before it can be decoded, so it has to be undone."""
    corrupt = b"\xff\xd8\xff" + b"\x9c\x1f" * 512
    bucket = settings.originals_dir / KIND

    def files() -> set[Path]:
        return {path for path in bucket.rglob("*") if path.is_file()} if bucket.exists() else set()

    before = files()
    with pytest.raises(images.ImageRejected):
        images.store_and_process(db, corrupt, "broken.jpg", "image/jpeg", kind=KIND)

    assert files() == before


# --------------------------------------------------------------------------
# HEIC on input (F51)
# --------------------------------------------------------------------------
def test_a_heic_photograph_is_accepted_and_served_as_webp(pipeline):
    """What the owner's phone writes, taken without a conversion step first.

    Nothing downstream learns a new format: the renditions are WebP exactly as
    they are for a JPEG, and only the kept original carries `.heic`.
    """
    stored = pipeline(
        make_image(2000, 1200, "HEIF"), filename="IMG_0042.HEIC", content_type="image/heic"
    )

    assert stored.original_path.endswith(".heic")
    assert (stored.width, stored.height) == (2000, 1200)
    assert sorted(stored.derivatives) == [640, 1600, 2000]
    assert size_of(stored.derivatives[640]) == (640, 384)
    for relative in stored.derivatives.values():
        assert relative.endswith(".webp")
        with Image.open(derived(relative)) as rendition:
            assert rendition.format == "WEBP"


def test_a_heic_is_rotated_before_it_is_measured(pipeline):
    """A phone stores the sensor's pixels and the orientation beside them.

    For HEIC the correction lands in the decoder rather than in
    `ImageOps.exif_transpose` — pillow-heif applies the tag on open — so this
    asserts the size the visitor is served, not which line produced it.
    """
    stored = pipeline(
        make_image(2000, 1200, "HEIF", orientation=6),
        filename="IMG_0043.HEIC",
        content_type="image/heic",
    )

    # Stored 2000×1200, displayed 1200×2000 — and the ladder follows the
    # displayed width, so no rendition is built from the un-rotated frame.
    assert (stored.width, stored.height) == (1200, 2000)
    assert sorted(stored.derivatives) == [640, 1200]
    assert size_of(stored.derivatives[640]) == (640, 1067)


def test_a_heic_with_no_content_type_is_left_to_the_magic_bytes():
    """Some browsers report no type for this format at all.

    The gate in the browser lets an unknown type through for exactly this
    reason, so the server has to be the one that decides — and it decides on the
    bytes, not on what the client called them.
    """
    assert images.validate_upload("IMG_0042.HEIC", "", make_image(320, 240, "HEIF")) == "image/heic"


def test_a_tiff_is_still_refused():
    """Accepting one more format is not accepting whatever Pillow can open."""
    with pytest.raises(images.ImageRejected):
        images.validate_upload("scan.tiff", "image/tiff", make_image(400, 300, "TIFF"))


@pytest.mark.parametrize(
    "key",
    [
        "photo.drop_note",
        "photo.file_wrong_type",
        "blog.cover_hint",
        "blog.image_wrong_type",
        "image.wrong_type",
    ],
)
def test_every_string_that_lists_the_accepted_formats_lists_all_of_them(key):
    """Copy is a gate too — the one the owner reads before he tries.

    Two of these were left saying «JPEG, PNG или WebP» after HEIC was accepted,
    which is the failure R-10 exists to prevent in its most expensive form: the
    owner converts the file himself because the drop zone told him to. Named by
    key rather than swept, so adding a sixth is a deliberate act.
    """
    text = translate(key)

    assert "HEIC" in text, key
    for known in ("JPEG", "PNG", "WebP"):
        assert known in text, key


@pytest.mark.parametrize(
    ("label", "data"),
    [
        # ISO-BMFF, `ftyp` in the right place — and a video. The brand at offset
        # 8 is the only thing separating it from a photograph.
        ("video", b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00" + b"\x00" * 48),
        ("not a media file at all", b"PK\x03\x04 this is a zip"),
    ],
)
def test_a_file_that_only_pretends_to_be_heic_is_refused(label, data):
    with pytest.raises(images.ImageRejected):
        images.validate_upload("IMG_0044.heic", "image/heic", data)


# --------------------------------------------------------------------------
# Removal
# --------------------------------------------------------------------------
def test_delete_files_removes_the_original_and_every_rendition(pipeline):
    stored = pipeline(make_image(2000, 1500))
    paths = [original(stored.original_path)] + [
        derived(relative) for relative in stored.derivatives.values()
    ]
    assert all(path.is_file() for path in paths)

    images.delete_files(stored.original_path, *stored.derivatives.values())

    assert not any(path.exists() for path in paths)


def test_delete_files_tolerates_paths_that_are_already_gone():
    images.delete_files(None, "", f"{KIND}/1999/does-not-exist.jpg")


def test_media_url_points_at_the_public_mount():
    assert images.media_url("photos/3-gory/abc_640.webp") == "/media/photos/3-gory/abc_640.webp"
    assert images.media_url(None) is None


# --------------------------------------------------------------------------
# T083 / F40 — one album's files live in one directory
# --------------------------------------------------------------------------
def test_files_are_filed_under_the_thing_they_belong_to():
    """Not by year. `album/2026/` put one album's photographs among everyone's."""
    group = images.group_name(12, "elbrus-s-severa")
    relative, absolute = images.store_original(
        make_image(40, 30), "image/jpeg", kind=images.PHOTOS, group=group
    )

    assert relative.startswith("photos/12-elbrus-s-severa/")
    assert absolute.parent.name == "12-elbrus-s-severa"
    assert absolute.parent.parent.name == "photos"
    images.delete_files(relative)


def test_a_rendition_lands_beside_its_own_original(db):
    group = images.group_name(3, "zametka")
    stored = images.store_and_process(
        db,
        make_image(900, 600),
        "shot.jpg",
        "image/jpeg",
        kind=images.POSTS,
        group=group,
        profile=images.COVER,
    )
    db.commit()

    original = Path(stored.original_path)
    for rendition in stored.derivatives.values():
        assert Path(rendition).parent == original.parent
    images.release(db, stored.original_path)


def test_a_frame_reused_under_a_richer_profile_gets_the_missing_rungs(pipeline):
    """A cover reused as a photograph must not stay on the cover's ladder.

    Deduplication is keyed on bytes, not on what the bytes were wanted for.
    `COVER` stops at 1600 px at quality 85 and never holds the frame's own
    width; the lightbox is exactly where that difference is visible. Without the
    top-up the second upload silently inherits the first one's ceiling and
    nothing ever revisits it — ADR-014's one property that must not fail, lost
    to a cache hit.
    """
    data = make_image(2001, 1334)

    first = pipeline(data, profile=images.COVER)
    assert sorted(first.derivatives) == [640, 1600]

    second = pipeline(data, profile=images.PHOTO)

    # Still one upload: same original, no second copy on disk (F42).
    assert second.original_path == first.original_path
    # …but now carrying every rung the photograph profile asks for.
    assert sorted(second.derivatives) == [640, 1600, 2001]
    assert derived(second.derivatives[2001]).is_file()


def test_missing_rungs_names_only_what_is_absent(pipeline, db):
    """The predicate the album upload branches on.

    Truthy sends a deduplicated upload to the background pool instead of
    marking it ready on the spot; empty keeps the fast path, which is what makes
    the common case free.
    """
    data = make_image(2001, 1334)
    pipeline(data, profile=images.COVER)

    asset = images.find_asset(db, images.content_digest(data))
    assert asset is not None
    assert images.missing_rungs(asset, images.PHOTO) == (2001,)
    assert images.missing_rungs(asset, images.COVER) == ()


@pytest.mark.parametrize(
    ("identifier", "slug", "expected"),
    [
        (12, "elbrus", "12-elbrus"),
        (12, "Эльбрус", "12"),  # a slug is transliterated upstream; nothing survives here
        (None, "chernovik", "chernovik"),
        (None, "", images.UNFILED),
        (7, "", "7"),
    ],
)
def test_group_names_are_stable_and_readable(identifier, slug, expected):
    assert images.group_name(identifier, slug) == expected


@pytest.mark.parametrize("hostile", ["../../etc", "a/../../b", "..", "/absolute", "with spaces"])
def test_a_group_can_never_climb_out_of_its_parent(hostile):
    group = images.safe_group(hostile)

    assert "/" not in group
    assert ".." not in group
    relative, _ = images.store_original(
        make_image(20, 20), "image/jpeg", kind=images.PHOTOS, group=hostile
    )
    assert relative.startswith(f"photos/{group}/")
    assert (
        (settings.originals_dir / relative)
        .resolve()
        .is_relative_to(settings.originals_dir.resolve())
    )
    images.delete_files(relative)
