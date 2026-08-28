"""shared_article: articles reachable only by their own secret link

Revision ID: a37da390e9d0
Revises: 9a4e77c1b208
Create Date: 2026-08-29 00:26:46.276370
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a37da390e9d0"
down_revision: str | None = "9a4e77c1b208"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shared_article",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("share_token", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_shared_article_share_token"), "shared_article", ["share_token"], unique=True
    )
    # `fk_album_cover_photo` also showed up in autogenerate's diff here — that FK
    # is unrelated to this table and pre-dates I8; left for whichever migration
    # actually owns it, not folded into a table this revision has no business
    # touching.


def downgrade() -> None:
    op.drop_index(op.f("ix_shared_article_share_token"), table_name="shared_article")
    op.drop_table("shared_article")
