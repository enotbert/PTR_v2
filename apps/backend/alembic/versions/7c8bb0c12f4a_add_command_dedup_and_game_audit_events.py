"""add command_dedup and game_audit_events

Revision ID: 7c8bb0c12f4a
Revises: e8f4a2b1c9d0
Create Date: 2026-05-04

Idempotency + audit tables (see docs/tech/data-model-v1-proposal.md §3.4, PTR-71).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7c8bb0c12f4a"
down_revision: str | Sequence[str] | None = "e8f4a2b1c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "command_dedup",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("player_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("room_kind", sa.String(length=32), nullable=False),
        sa.Column("room_id", sa.String(length=128), nullable=False),
        sa.Column("client_command_id", sa.String(length=128), nullable=False),
        sa.Column("command_type", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("result_kind", sa.String(length=32), nullable=False),
        sa.Column("original_server_seq", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id",
            "room_kind",
            "room_id",
            "client_command_id",
            name="uq_command_dedup_player_room_client",
        ),
    )
    op.create_index("ix_command_dedup_player_id", "command_dedup", ["player_id"], unique=False)

    op.create_table(
        "game_audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("player_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_game_audit_events_player_id",
        "game_audit_events",
        ["player_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_audit_events_session_id",
        "game_audit_events",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_audit_events_event_name",
        "game_audit_events",
        ["event_name"],
        unique=False,
    )
    op.create_index(
        "ix_game_audit_events_event_at",
        "game_audit_events",
        ["event_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_game_audit_events_event_at", table_name="game_audit_events")
    op.drop_index("ix_game_audit_events_event_name", table_name="game_audit_events")
    op.drop_index("ix_game_audit_events_session_id", table_name="game_audit_events")
    op.drop_index("ix_game_audit_events_player_id", table_name="game_audit_events")
    op.drop_table("game_audit_events")
    op.drop_index("ix_command_dedup_player_id", table_name="command_dedup")
    op.drop_table("command_dedup")
