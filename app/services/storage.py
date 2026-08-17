"""What is on disk, and what nothing on the site points at (ADR-037).

One walk, two callers: «Медиа» in the cabinet renders it when the owner presses
«Проверить», and `scripts/media_orphans.py` prints it from the command line. The
walk used to live in the script alone, and copying it into a router would have
left two implementations of "what is an orphan" free to disagree — the same drift
ADR-013 built `owners_of` to avoid.

**Nothing here deletes anything.** The scan is a read of the filesystem and of
the content tables; `images.release` is the only thing that unlinks a file, and
the script's `--prune` is the only thing that calls it. That is deliberate: a
prune is a decision to take on a server, after reading what would go.

Both media roots are walked together. An original and its renditions are one
thing to keep or to delete, and looking at either root alone would call half of a
live upload an orphan.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.services.images import owners_of, stem_of


@dataclass(frozen=True)
class Upload:
    """One upload as it exists on disk, and everything that still points at it.

    `owners` comes from `images.owners_of`, so it is the same answer the pages
    are built from rather than a stored count.
    """

    stem: str
    files: list[Path]
    owners: list[str]

    @property
    def byte_size(self) -> int:
        """Asked of the filesystem, and tolerant of a file removed mid-walk."""
        return sum(path.stat().st_size for path in self.files if path.exists())

    @property
    def is_orphan(self) -> bool:
        return not self.owners

    @property
    def is_shared(self) -> bool:
        """One upload, several pages — since the same bytes are stored once (F42).

        Not a problem to fix; a thing to know before editing the tree by hand,
        because `tar`-ing one article's directory can carry a file another
        article needs.
        """
        return len(self.owners) > 1


@dataclass(frozen=True)
class DiskScan:
    """Every upload on disk, sorted by stem, as both callers want to read it.

    Deliberately *not* carrying the empty directories: the script walks for those
    **after** a `--prune`, so that a directory the prune emptied is reported and
    removed in the same run. Folding them in here would have moved that walk to
    before the deletion and quietly changed what the command does.
    """

    uploads: list[Upload]

    @property
    def file_count(self) -> int:
        return sum(len(upload.files) for upload in self.uploads)

    @property
    def orphans(self) -> list[Upload]:
        return [upload for upload in self.uploads if upload.is_orphan]

    @property
    def shared(self) -> list[Upload]:
        return [upload for upload in self.uploads if upload.is_shared]

    @property
    def orphan_bytes(self) -> int:
        return sum(upload.byte_size for upload in self.orphans)


def group_by_stem() -> dict[str, list[Path]]:
    """Every file under both media roots, grouped by the upload it belongs to."""
    grouped: dict[str, list[Path]] = {}
    for root in (settings.originals_dir, settings.derived_dir):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            grouped.setdefault(stem_of(relative), []).append(path)
    return grouped


def empty_directories() -> list[Path]:
    """Directories holding nothing, deepest first so a parent empties in turn.

    Deleting a photo prunes what it empties, but the tree still carries the
    directories of everything removed before that was true — every e2e album,
    and the `post/` and `album/` roots the year-based layout used.
    """
    found: list[Path] = []
    for root in (settings.originals_dir, settings.derived_dir):
        if not root.is_dir():
            continue
        for directory in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                found.append(directory)
    return found


def scan(db: Session) -> DiskScan:
    """Walk both roots and ask the content tables who owns each upload.

    A filesystem walk plus a handful of `LIKE` scans per upload, which is why the
    cabinet runs it on a press and never on page load (ADR-037).
    """
    return DiskScan(
        uploads=[
            Upload(stem=stem, files=paths, owners=owners_of(db, stem))
            for stem, paths in sorted(group_by_stem().items())
        ]
    )
