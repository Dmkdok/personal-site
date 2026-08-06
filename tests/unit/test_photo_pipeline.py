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
def pipeline():
    """Run the pipeline and clean every file it wrote, pass or fail."""
    written: list[str] = []

    def run(data: bytes, filename: str = "shot.jpg", content_type: str = "image/jpeg"):
        stored = images.store_and_process(data, filename, content_type, kind=KIND)
        written.append(stored.original_path)
        written.extend(stored.derivatives.values())
        return stored

    yield run
    images.delete_files(*written)


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

    assert sorted(stored.derivatives) == [640, 1600, 2560]
    assert (stored.width, stored.height) == (3000, 2000)
    for width in (640, 1600, 2560):
        assert size_of(stored.derivatives[width]) == (width, round(2000 * width / 3000))


def test_portrait_keeps_its_aspect_ratio(pipeline):
    stored = pipeline(make_image(1200, 1800))

    # 1600 and 2560 are wider than the original, so they are simply not made.
    assert sorted(stored.derivatives) == [640]
    assert (stored.width, stored.height) == (1200, 1800)
    assert size_of(stored.derivatives[640]) == (640, 960)


def test_an_image_smaller_than_the_smallest_target_is_not_upscaled(pipeline):
    stored = pipeline(make_image(400, 300))

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


def test_a_rejected_upload_leaves_nothing_behind():
    """The original is written before it can be decoded, so it has to be undone."""
    corrupt = b"\xff\xd8\xff" + b"\x9c\x1f" * 512
    bucket = settings.originals_dir / KIND

    def files() -> set[Path]:
        return {path for path in bucket.rglob("*") if path.is_file()} if bucket.exists() else set()

    before = files()
    with pytest.raises(images.ImageRejected):
        images.store_and_process(corrupt, "broken.jpg", "image/jpeg", kind=KIND)

    assert files() == before


# --------------------------------------------------------------------------
# Removal
# --------------------------------------------------------------------------
def test_delete_files_removes_the_original_and_every_rendition():
    stored = images.store_and_process(make_image(2000, 1500), "shot.jpg", "image/jpeg", kind=KIND)
    paths = [original(stored.original_path)] + [
        derived(relative) for relative in stored.derivatives.values()
    ]
    assert all(path.is_file() for path in paths)

    images.delete_files(stored.original_path, *stored.derivatives.values())

    assert not any(path.exists() for path in paths)


def test_delete_files_tolerates_paths_that_are_already_gone():
    images.delete_files(None, "", f"{KIND}/1999/does-not-exist.jpg")


def test_media_url_points_at_the_public_mount():
    assert images.media_url("album/2026/abc_640.webp") == "/media/album/2026/abc_640.webp"
    assert images.media_url(None) is None
