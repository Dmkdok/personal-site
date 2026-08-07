"""Move the media tree to the per-album / per-article layout (T083, F40).

Files used to be filed by year — `originals/album/2026/<uuid>.jpg` — which put
one album's photographs among every other album's. They now live under a
directory of their own inside a logical parent:

    originals/photos/<album-id>-<slug>/<uuid>.jpg
    derived/photos/<album-id>-<slug>/<uuid>_640.webp
    originals/posts/<post-id>-<slug>/<uuid>.jpg
    derived/projects/<project-id>-<slug>/<uuid>_1600.webp

Three things have to move together or the site breaks: the files, the paths
recorded in `photo`, `post` and `project`, and the `/media/...` URLs written
into article bodies — both the Markdown the owner edits and the rendered HTML
that is served.

    docker compose run --rm web python scripts/migrate_media.py           # dry run
    docker compose run --rm web python scripts/migrate_media.py --apply

Safe to run twice: anything already in the new layout is left alone. Take a
backup first — `make backup` — because this moves files.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import engine
from app.models.album import Album
from app.models.photo import Photo
from app.models.post import Post
from app.models.project import Project
from app.models.site_content import SiteContent
from app.services.images import PHOTOS, POSTS, PROJECTS, group_name

# The layout this script migrates *from*: `<kind>/<yyyy>/<name>`.
OLD = re.compile(r"^(album|post|project)/\d{4}/(?P<name>[^/]+)$")

NEW_KIND = {"album": PHOTOS, "post": POSTS, "project": PROJECTS}


@dataclass
class Plan:
    moves: dict[str, str] = field(default_factory=dict)
    rows: list[str] = field(default_factory=list)
    rewrites: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def relocate(self, old: str, group: str) -> str | None:
        """Record the move for one stored path; return its new value."""
        match = OLD.match(old)
        if not match:
            self.skipped.append(old)
            return None
        new = f"{NEW_KIND[match.group(1)]}/{group}/{match.group('name')}"
        self.moves[old] = new
        return new


def _plan(db: Session) -> Plan:
    plan = Plan()

    for photo, album in db.execute(select(Photo, Album).join(Album, Photo.album_id == Album.id)):
        group = group_name(album.id, album.slug)
        for column in ("original_path", "thumb_path", "medium_path", "large_path"):
            old = getattr(photo, column)
            if old and plan.relocate(old, group):
                plan.rows.append(f"photo {photo.id}.{column}")

    for post in db.scalars(select(Post)):
        group = group_name(post.id, post.slug)
        if post.cover_path and plan.relocate(post.cover_path, group):
            plan.rows.append(f"post {post.id}.cover_path")
        # A cover's original keeps the derivative's stem with its own extension.
        if post.cover_path:
            _plan_original_of(plan, post.cover_path, group)
        # Pictures inside the article body are referenced by URL, not by column.
        for column in ("body_md", "body_html"):
            for old in _media_paths_in(getattr(post, column) or ""):
                if plan.relocate(old, group):
                    plan.rewrites.append(f"post {post.id}.{column}")

    for project in db.scalars(select(Project)):
        group = group_name(project.id, project.slug)
        if project.cover_path and plan.relocate(project.cover_path, group):
            plan.rows.append(f"project {project.id}.cover_path")
        if project.cover_path:
            _plan_original_of(plan, project.cover_path, group)

    return plan


_DERIVATIVE = re.compile(r"_\d+\.webp$")
_ORIGINAL_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
_MEDIA_URL = re.compile(r"/media/((?:album|post|project)/\d{4}/[^\"'\s)]+)")


def _media_paths_in(text: str) -> list[str]:
    return _MEDIA_URL.findall(text)


def _plan_original_of(plan: Plan, cover_path: str, group: str) -> None:
    """Covers store only their derivative; the original sits beside it."""
    stem = _DERIVATIVE.sub("", cover_path)
    for extension in _ORIGINAL_EXTENSIONS:
        candidate = f"{stem}{extension}"
        if (settings.originals_dir / candidate).exists():
            plan.relocate(candidate, group)


def _move_files(plan: Plan, *, apply: bool) -> tuple[int, int]:
    """Move each planned file from whichever root holds it.

    A given path lives in exactly one of the two roots — an original in
    `originals/`, a rendition in `derived/` — so 'not found' means not found in
    either, not merely absent from one.
    """
    moved = missing = 0
    for old, new in plan.moves.items():
        found = False
        for root in (settings.originals_dir, settings.derived_dir):
            source, target = root / old, root / new
            if target.exists():
                found = True  # already migrated
                continue
            if not source.exists():
                continue
            found = True
            moved += 1
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                source.replace(target)
        if not found:
            missing += 1
    return moved, missing


def _rewrite_rows(db: Session, plan: Plan) -> None:
    for photo in db.scalars(select(Photo)):
        for column in ("original_path", "thumb_path", "medium_path", "large_path"):
            old = getattr(photo, column)
            if old in plan.moves:
                setattr(photo, column, plan.moves[old])

    for post in db.scalars(select(Post)):
        if post.cover_path in plan.moves:
            post.cover_path = plan.moves[post.cover_path]
        post.body_md = _rewrite_urls(post.body_md or "", plan)
        post.body_html = _rewrite_urls(post.body_html or "", plan)

    for project in db.scalars(select(Project)):
        if project.cover_path in plan.moves:
            project.cover_path = plan.moves[project.cover_path]

    for block in db.scalars(select(SiteContent)):
        block.value_md = _rewrite_urls(block.value_md or "", plan)
        block.value_html = _rewrite_urls(block.value_html or "", plan)


def _rewrite_urls(text: str, plan: Plan) -> str:
    def swap(match: re.Match[str]) -> str:
        old = match.group(1)
        return f"/media/{plan.moves.get(old, old)}"

    return _MEDIA_URL.sub(swap, text)


def _orphans() -> list[Path]:
    """Files still in the old `<kind>/<yyyy>/` layout that nothing points at.

    Left where they are on purpose. They are the residue of deleted articles and
    abandoned uploads, and deleting other people's files is not a migration's
    job — it reports them so the owner can decide.
    """
    found: list[Path] = []
    for root in (settings.originals_dir, settings.derived_dir):
        for old_kind in ("album", "post", "project"):
            found.extend(sorted((root / old_kind).rglob("*.*")))
    return found


def _prune_empty_directories() -> None:
    """Leave no `album/2026/` behind to be mistaken for live storage."""
    for root in (settings.originals_dir, settings.derived_dir):
        for directory in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="actually move files and rewrite rows")
    args = parser.parse_args()

    with Session(engine) as db:
        plan = _plan(db)

        print(f"media root: {settings.media_root}")
        print(f"{len(plan.moves)} file(s) to relocate")
        for old, new in list(plan.moves.items())[:20]:
            print(f"  {old}  ->  {new}")
        if len(plan.moves) > 20:
            print(f"  … and {len(plan.moves) - 20} more")
        print(f"{len(plan.rows)} database column(s), {len(plan.rewrites)} body rewrite(s)")
        if plan.skipped:
            print(f"{len(plan.skipped)} path(s) already in the new layout or unrecognised")

        moved, missing = _move_files(plan, apply=args.apply)
        print(f"{moved} file(s) {'moved' if args.apply else 'would move'}, {missing} not on disk")

        if not args.apply:
            print("\nDry run. Re-run with --apply to carry it out.")
            return 0

        _rewrite_rows(db, plan)
        db.commit()
        _prune_empty_directories()

        left = _orphans()
        if left:
            print(f"\n{len(left)} file(s) left in the old layout that nothing references:")
            for path in left[:10]:
                print(f"  {path.relative_to(settings.media_root)}")
            if len(left) > 10:
                print(f"  … and {len(left) - 10} more")
            print("  Residue of deleted articles and abandoned uploads. Yours to delete.")

        print("\nDone. Database and disk are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
