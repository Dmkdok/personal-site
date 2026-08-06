"""Background work: a small thread pool plus a startup recovery hook.

Sized for the real load — one person uploading one album at a time. The app
runs a single Uvicorn worker so this state stays coherent; scaling out would
mean replacing this with a real queue (see ADR-004).
"""

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.db import SessionLocal

logger = logging.getLogger("portfolio.background")

# The pool is created on first use and dropped on shutdown, rather than being
# built once at import time. A ThreadPoolExecutor cannot be restarted, so a
# module-level instance turns the first `shutdown()` into a process-wide kill:
# under pytest, where every TestClient runs the lifespan, the first teardown
# would leave every later `submit()` raising "cannot schedule new futures after
# shutdown". Production still builds one pool and shuts it down once.
_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = None
_recovery_hooks: list[Callable[[], None]] = []


def _pool() -> ThreadPoolExecutor:
    global _executor
    with _lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bg")
        return _executor


def submit(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Run `fn` off the request path. Exceptions are logged, never swallowed silently."""

    def runner() -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("background task %s failed", getattr(fn, "__name__", fn))

    _pool().submit(runner)


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

    _pool().submit(runner)


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
    """Drop the pool. Idempotent, and a later `submit()` builds a fresh one."""
    global _executor
    with _lock:
        executor, _executor = _executor, None
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=False)
