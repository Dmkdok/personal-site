"""Cache busting for `/static` assets.

Caddy serves `/static/*` with `max-age=604800`, so the version query is the only
thing that reaches a returning visitor after a CSS- or JS-only release. It used
to be keyed on `templating.py`'s own mtime, which moves for neither a restart
nor a stylesheet edit — meaning a week of stale files, invisible in development
because there is no proxy there and `./app` is bind-mounted.
"""

import os
import re

import pytest

from app import templating
from app.templating import STATIC_DIR, static_url

VERSIONED = re.compile(r"^/static/(?P<path>.+)\?v=(?P<version>\d+)$")


def parse(url: str) -> re.Match[str]:
    match = VERSIONED.match(url)
    assert match is not None, f"not a versioned static URL: {url}"
    return match


@pytest.fixture
def static_dir(tmp_path, monkeypatch):
    """Point `static_url` at a scratch tree so mtimes can be moved at will."""
    monkeypatch.setattr(templating, "STATIC_DIR", tmp_path)
    return tmp_path


def write(root, relative: str, content: str = "body{}") -> os.PathLike:
    asset = root / relative
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text(content, encoding="utf-8")
    return asset


# --------------------------------------------------------------------------
# The version is the asset's own


def test_version_is_the_assets_own_mtime(static_dir):
    asset = write(static_dir, "css/base.css")

    match = parse(static_url("css/base.css"))

    assert match["path"] == "css/base.css"
    assert match["version"] == str(int(asset.stat().st_mtime))


def test_editing_an_asset_changes_its_version(static_dir):
    asset = write(static_dir, "css/base.css")
    before = parse(static_url("css/base.css"))["version"]

    moved = asset.stat().st_mtime + 120
    os.utime(asset, (moved, moved))

    assert parse(static_url("css/base.css"))["version"] != before


def test_two_assets_edited_apart_do_not_share_a_version(static_dir):
    """The shape of the defect: every asset carried one module-wide number."""
    first = write(static_dir, "css/base.css")
    second = write(static_dir, "js/ui.js", "//")

    moved = first.stat().st_mtime + 300
    os.utime(second, (moved, moved))

    assert parse(static_url("css/base.css"))["version"] != parse(static_url("js/ui.js"))["version"]


def test_version_is_not_the_modules_mtime(static_dir):
    """What it was before, and what it must never fall back to for a real file."""
    asset = write(static_dir, "css/base.css")
    moved = os.stat(templating.__file__).st_mtime + 3600
    os.utime(asset, (moved, moved))

    assert parse(static_url("css/base.css"))["version"] != templating._FALLBACK_ASSET_VERSION


# --------------------------------------------------------------------------
# Shape and edges


def test_a_missing_asset_still_renders(static_dir):
    """A template naming a file that is not there is a bug, not a 500."""
    assert parse(static_url("css/gone.css"))["version"] == templating._FALLBACK_ASSET_VERSION


def test_a_leading_slash_is_accepted(static_dir):
    write(static_dir, "css/base.css")

    assert parse(static_url("/css/base.css"))["path"] == "css/base.css"


def test_it_works_against_the_real_static_tree():
    """Guards STATIC_DIR itself: the shipped stylesheet must resolve on disk."""
    asset = STATIC_DIR / "css" / "base.css"
    assert asset.is_file(), f"expected a stylesheet at {asset}"

    assert parse(static_url("css/base.css"))["version"] == str(int(asset.stat().st_mtime))
