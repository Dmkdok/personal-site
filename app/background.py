"""Background work: a small thread pool plus a startup recovery hook.

Sized for the real load — one person uploading one album at a time. The app
runs a single Uvicorn worker so this state stays coherent; scaling out would
mean replacing this with a real queue (see ADR-004).
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.db import SessionLocal

logger = logging.getLogger("portfolio.background")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bg")
_recovery_hooks: list[Callable[[], None]] = []


def submit(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Run `fn` off the request path. Exceptions are logged, never swallowed silently."""

    def runner() -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("background task %s failed", getattr(fn, "__name__", fn))

    _executor.submit(runner)


def submit_with_session(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Same, but hands the task its own database session and always closes it."""

    def runner() -> None:
        db = SessionLocal()
        try:
            fn(db, *args, **kwargs)
        except Exception:
            db.rollback()
            logger.exception("background task %s failed", getattr(fn, "__name__", fn))
        finally:
            db.close()

    _executor.submit(runner)


def register_recovery(hook: Callable[[], None]) -> Callable[[], None]:
    """Register work to run once at startup — e.g. re-queue photos left mid-processing."""
    _recovery_hooks.append(hook)
    return hook


def run_recovery() -> None:
    for hook in _recovery_hooks:
        try:
            hook()
        except Exception:
            logger.exception("recovery hook %s failed", getattr(hook, "__name__", hook))


def shutdown() -> None:
    _executor.shutdown(wait=False, cancel_futures=False)
