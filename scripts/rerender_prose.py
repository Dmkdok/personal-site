"""Re-render the stored HTML from the Markdown it came from.

`body_html` / `value_html` are produced once, the moment the owner saves, and
served verbatim ever after. So a change to `app.services.markdown` reaches new
writing only: articles already published keep whatever markup the renderer
emitted on the day they were written. Adding `width`/`height` to in-article
pictures (the CLS fix) is exactly that kind of change.

This re-renders every stored row from the `*_md` column that produced it. It
invents nothing and reads no Markdown of its own, so running it twice does
nothing the first run did not, and running it on an untouched database prints
"0 rows".

    docker compose run --rm web python scripts/rerender_prose.py           # dry run
    docker compose run --rm web python scripts/rerender_prose.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.models.post import Post
from app.models.project import Project
from app.models.site_content import SiteContent
from app.services.markdown import render_markdown

#: Every table that stores rendered Markdown, with the column pair and
#: something human-readable to name the row by.
TABLES = (
    (Post, "body_md", "body_html", lambda row: row.slug),
    (Project, "body_md", "body_html", lambda row: row.slug),
    (SiteContent, "value_md", "value_html", lambda row: row.key),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-render stored HTML from stored Markdown.")
    parser.add_argument("--apply", action="store_true", help="write the rows back")
    args = parser.parse_args()

    stale = 0
    with Session(engine) as session:
        for model, md_column, html_column, label in TABLES:
            for row in session.scalars(select(model)):
                if not getattr(row, html_column):
                    # A row that stores no HTML is not a Markdown row. The
                    # social links and the copyright name are plain text and
                    # `pages._put_value` blanks their HTML on purpose, so that
                    # a stray `*` in a name can never reach an href. Rendering
                    # them here would undo that decision silently.
                    continue
                fresh = render_markdown(getattr(row, md_column) or "")
                if fresh == getattr(row, html_column):
                    continue
                stale += 1
                print(f"{model.__name__} {label(row)}: {html_column} is out of date")
                if args.apply:
                    setattr(row, html_column, fresh)
        if args.apply:
            session.commit()

    verb = "rewritten" if args.apply else "would be rewritten"
    print(f"\n{stale} row(s) {verb}.")
    if stale and not args.apply:
        print("Re-run with --apply to write them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
