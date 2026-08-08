"""Report — and optionally delete — media files nothing on the site references.

    docker compose run --rm web python scripts/media_orphans.py            # report
    docker compose run --rm web python scripts/media_orphans.py --prune    # delete

The application never leaves an orphan behind by itself: deleting an article, a
project, an album or a picture releases its files, and a file another page still
uses is kept (F41, ADR-013). This script exists for the residue of everything
that happened *before* that was true — deleted articles from earlier milestones,
uploads abandoned halfway — and as the answer to "what is actually in there?".

It also reports **shared** files: since the same bytes are stored once (F42), a
frame used by two articles physically sits in the directory of whichever one
uploaded it first. That matters if the tree is ever edited by hand, because
`tar`-ing one article's directory can carry a file another article needs.

Nothing is deleted without `--prune`, and a prune deletes only what the database
says nobody points at — it asks the same question `release` asks on every
deletion, so running it twice is as safe as running it once.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.config import settings
from app.db import engine
from app.services.images import owners_of, release, stem_of


def _stems() -> dict[str, list[Path]]:
    """Every file under the media root, grouped by the upload it belongs to.

    Both roots at once: an original and its renditions are one thing to keep or
    to delete, and looking at either alone would call half of a live upload an
    orphan.
    """
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


def _empty_directories() -> list[Path]:
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


def _size(paths: list[Path]) -> int:
    return sum(path.stat().st_size for path in paths if path.exists())


def _human(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prune", action="store_true", help="delete the orphans after listing them"
    )
    args = parser.parse_args()

    grouped = _stems()
    print(f"media root: {settings.media_root}")
    print(f"{sum(len(paths) for paths in grouped.values())} file(s) in {len(grouped)} upload(s)\n")

    with Session(engine) as db:
        orphans: list[str] = []
        shared: list[tuple[str, list[str]]] = []

        for stem, paths in sorted(grouped.items()):
            owners = owners_of(db, stem)
            if not owners:
                orphans.append(stem)
                print(f"ORPHAN  {stem}  ({len(paths)} file(s), {_human(_size(paths))})")
            elif len(owners) > 1:
                shared.append((stem, owners))

        if shared:
            print(f"\n{len(shared)} upload(s) shared by more than one owner:")
            for stem, owners in shared:
                print(f"  {stem}")
                for owner in owners:
                    print(f"      used by {owner}")
            print("  One file, several pages. Do not delete these by hand.")

        if orphans:
            freed = sum(_size(grouped[stem]) for stem in orphans)
            print(f"\n{len(orphans)} orphaned upload(s), {_human(freed)}")
            if args.prune:
                # `release` re-asks the database before it unlinks anything, so a
                # row written since the listing above still saves its file.
                release(db, *orphans)
                print(f"Deleted {len(orphans)} orphaned upload(s), freeing {_human(freed)}.")
            else:
                print("Nothing deleted. Re-run with --prune to remove them.")
        else:
            print("\nNo orphaned files.")

    empty = _empty_directories()
    if empty:
        print(f"\n{len(empty)} empty director(ies):")
        for directory in empty[:10]:
            print(f"  {directory.relative_to(settings.media_root)}")
        if len(empty) > 10:
            print(f"  … and {len(empty) - 10} more")
        if args.prune:
            # The listing above is a moment old, and an upload landing in the
            # meantime refills one of these. `rmdir` refuses a non-empty
            # directory, which is the right answer — but unguarded it would end
            # the run on a traceback *after* the files were already deleted, and
            # a successful prune would read as a failed one.
            removed = 0
            for directory in empty:
                try:
                    directory.rmdir()
                except OSError as exc:
                    print(f"  kept {directory.relative_to(settings.media_root)}: {exc.strerror}")
                else:
                    removed += 1
            print(f"Removed {removed} empty director(ies).")

    if not args.prune and (orphans or empty):
        print("\nNothing was deleted. Re-run with --prune.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
