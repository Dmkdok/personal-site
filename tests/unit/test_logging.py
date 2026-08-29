"""T126 / F58 — the log as a file on disk, and never a reason the site is down.

The container's stdout is the only copy of the log today, which means reading it
needs a Docker client on the NAS. `LOG_DIR` puts a second copy on a bind-mounted
directory the owner can open over the share. It is empty by default, so a
developer's checkout and this suite write nothing new.
"""

import logging

import pytest

from app.config import settings
from app.main import _configure_logging, _RedactShareTokenFromAccessLog, redact_share_token


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


# --------------------------------------------------------------------------
# REVIEW.md run 10, M-1 — `share_token` is a bearer credential (ADR-042,
# ADR-043) and must never reach a log line in plaintext: neither the access
# log uvicorn writes for every `GET /s/{share_token}`, nor the unhandled-
# exception handler, which used to log `request.url.path` verbatim.
# --------------------------------------------------------------------------
def test_redact_share_token_keeps_everything_but_the_token():
    assert redact_share_token("/s/AbCd-123_xyz") == "/s/<redacted>"
    assert redact_share_token("/blog/some-post") == "/blog/some-post"
    assert redact_share_token("/") == "/"


def test_redact_share_token_stops_at_the_next_slash_or_query():
    # A token is one path segment — nothing after it is swallowed.
    assert redact_share_token("/s/tok123/edit") == "/s/<redacted>/edit"
    assert redact_share_token("/s/tok123?x=1") == "/s/<redacted>?x=1"


def _access_record(path: str) -> logging.LogRecord:
    # The shape uvicorn's AccessFormatter reads: (client_addr, method,
    # full_path, http_version, status_code).
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:12345", "GET", path, "1.1", 200),
        exc_info=None,
    )


def test_access_log_filter_redacts_the_path_argument_only():
    record = _access_record("/s/thetokenitself")

    assert _RedactShareTokenFromAccessLog().filter(record) is True
    assert record.args == ("127.0.0.1:12345", "GET", "/s/<redacted>", "1.1", 200)


def test_access_log_filter_leaves_an_ordinary_path_alone():
    record = _access_record("/blog/some-post")

    _RedactShareTokenFromAccessLog().filter(record)

    assert record.args == ("127.0.0.1:12345", "GET", "/blog/some-post", "1.1", 200)


def test_configuring_logging_repeatedly_does_not_stack_the_filter():
    """`_configure_logging` runs once per worker, and again per direct call in
    this file — the filter must not accumulate and redact N times over."""
    _configure_logging()
    _configure_logging()

    filters = logging.getLogger("uvicorn.access").filters
    redactors = [f for f in filters if isinstance(f, _RedactShareTokenFromAccessLog)]
    assert len(redactors) == 1
