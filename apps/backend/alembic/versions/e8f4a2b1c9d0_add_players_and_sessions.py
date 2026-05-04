"""add players and sessions

Revision ID: e8f4a2b1c9d0
Revises: 4af33f882465
Create Date: 2026-05-04

Identity tables for v1 player/session (see docs/tech/data-model-v1-proposal.md).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8f4a2b1c9d0"
down_revision: str | Sequence[str] | None = "4af33f882465"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("player_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("device_fingerprint", sa.String(256), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ip", sa.String(64), nullable=True),
        sa.Column("last_user_agent", sa.String(512), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_player_id", "sessions", ["player_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sessions_player_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("players")
