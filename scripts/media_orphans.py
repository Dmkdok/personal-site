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
from app.services.images import release
from app.services.storage import empty_directories, scan


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

    # The walk itself lives in `app.services.storage`, which the cabinet's
    # «Медиа» room also calls (ADR-037): one answer to "what is an orphan",
    # printed here and rendered there. This file keeps the part that is only a
    # command line's — the terminal formatting, and `--prune`.
    with Session(engine) as db:
        disk = scan(db)

        print(f"media root: {settings.media_root}")
        print(f"{disk.file_count} file(s) in {len(disk.uploads)} upload(s)\n")

        for upload in disk.orphans:
            print(
                f"ORPHAN  {upload.stem}  ({len(upload.files)} file(s), {_human(upload.byte_size)})"
            )

        if disk.shared:
            print(f"\n{len(disk.shared)} upload(s) shared by more than one owner:")
            for upload in disk.shared:
                print(f"  {upload.stem}")
                for owner in upload.owners:
                    print(f"      used by {owner}")
            print("  One file, several pages. Do not delete these by hand.")

        if disk.orphans:
            freed = disk.orphan_bytes
            print(f"\n{len(disk.orphans)} orphaned upload(s), {_human(freed)}")
            if args.prune:
                # `release` re-asks the database before it unlinks anything, so a
                # row written since the listing above still saves its file.
                release(db, *[upload.stem for upload in disk.orphans])
                print(f"Deleted {len(disk.orphans)} orphaned upload(s), freeing {_human(freed)}.")
            else:
                print("Nothing deleted. Re-run with --prune to remove them.")
        else:
            print("\nNo orphaned files.")

    # After the prune, deliberately: a directory the prune just emptied is
    # reported and removed in the same run, which is why this walk is not part of
    # `scan()`.
    empty = empty_directories()
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

    if not args.prune and (disk.orphans or empty):
        print("\nNothing was deleted. Re-run with --prune.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
