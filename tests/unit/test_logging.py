"""T126 / F58 — the log as a file on disk, and never a reason the site is down.

The container's stdout is the only copy of the log today, which means reading it
needs a Docker client on the NAS. `LOG_DIR` puts a second copy on a bind-mounted
directory the owner can open over the share. It is empty by default, so a
developer's checkout and this suite write nothing new.
"""

import logging

import pytest

from app.config import settings
from app.main import _configure_logging


@pytest.fixture
def clean_root():
    """Hand back whatever handlers the test adds to the root logger."""
    root = logging.getLogger()
    before = list(root.handlers)
    yield before
    for handler in list(root.handlers):
        if handler not in before:
            root.removeHandler(handler)
            handler.close()


def test_without_log_dir_no_file_handler_is_added(clean_root, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "log_dir", "")

    _configure_logging()

    assert logging.getLogger().handlers == clean_root
    assert list(tmp_path.iterdir()) == []


def test_with_log_dir_a_line_reaches_app_log_and_stdout_is_kept(
    clean_root, monkeypatch, tmp_path, caplog
):
    monkeypatch.setattr(settings, "log_dir", str(tmp_path))

    _configure_logging()
    # `basicConfig` cannot set the level here — pytest's logging plugin has
    # already put handlers on the root logger, which makes it a no-op. Under
    # uvicorn it is not, and INFO is what the application actually runs at.
    with caplog.at_level(logging.INFO):
        logging.getLogger("portfolio").info("a real line, %s", "written to disk")

    written = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "a real line, written to disk" in written

    # The file is *added*, never substituted: `docker logs` still shows everything.
    assert all(handler in logging.getLogger().handlers for handler in clean_root)


def test_an_unwritable_log_dir_warns_and_the_application_still_starts(
    clean_root, monkeypatch, tmp_path, caplog
):
    """A log path must never be the reason the site is down (I3 non-negotiable)."""
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("a regular file stands where the directory would go", encoding="utf-8")

    monkeypatch.setattr(settings, "log_dir", str(blocked / "logs"))

    with caplog.at_level(logging.WARNING):
        _configure_logging()  # must not raise

    assert any("log" in record.message.lower() for record in caplog.records)
    assert logging.getLogger().handlers == clean_root
