"""media_asset: content-hash deduplication of uploads

Revision ID: 7c1f0a2b4d31
Revises: 499da650c43f
Create Date: 2026-08-08 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c1f0a2b4d31"
down_revision: str | None = "499da650c43f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_asset",
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("stem", sa.String(length=300), nullable=False),
        sa.Column("original_path", sa.String(length=300), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("sha256"),
    )
    op.create_index(op.f("ix_media_asset_stem"), "media_asset", ["stem"], unique=False)
    # Files already on disk get no rows: the table describes what we know the
    # hash of, and nothing here knows the hash of an upload from last week.
    # The consequence is one missed deduplication per pre-existing file, which
    # `scripts/media_orphans.py` reports and nobody has to act on.


def downgrade() -> None:
    op.drop_index(op.f("ix_media_asset_stem"), table_name="media_asset")
    op.drop_table("media_asset")
