"""footer.rights holds the whole copyright line, not just the name

Revision ID: 9a4e77c1b208
Revises: 7c1f0a2b4d31
Create Date: 2026-08-08 12:30:00.000000
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "9a4e77c1b208"
down_revision: str | None = "7c1f0a2b4d31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The year the template used to supply. Frozen into the migration on purpose:
#: replaying this in 2031 must reproduce what the site showed the day it ran,
#: not stamp a year nobody chose.
_YEAR = datetime.now(UTC).year


def upgrade() -> None:
    """Prefix the stored name with what the template used to add in front of it.

    `© {{ current_year }} {{ rights }}` rendered the symbol and the year around
    a stored name; now the row holds the line itself (ADR-015). Migrating the
    existing value this way means nothing changes visibly on the day it ships.

    Rows that already start with the symbol are left alone, so this is safe to
    replay.
    """
    op.execute(
        sa.text(
            "UPDATE site_content "
            f"SET value_md = '© {_YEAR} ' || value_md "
            "WHERE key = 'footer.rights' AND value_md <> '' AND value_md NOT LIKE '©%'"
        )
    )


def downgrade() -> None:
    """Strip a leading `© <year> ` again, leaving anything else as it stands."""
    op.execute(
        sa.text(
            "UPDATE site_content "
            "SET value_md = regexp_replace(value_md, '^© [0-9]{4} ', '') "
            "WHERE key = 'footer.rights'"
        )
    )
