"""add tavern party raid tables

Revision ID: d4f0a6b8c201
Revises: 7c8bb0c12f4a
Create Date: 2026-05-06

DDL for persistent tavern / party / raid models (ORM in app.models.tavern, party_raid).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4f0a6b8c201"
down_revision: str | Sequence[str] | None = "7c8bb0c12f4a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "taverns",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_taverns_slug", "taverns", ["slug"], unique=True)

    op.create_table(
        "player_tavern_state",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("player_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tavern_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("reputation", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("weekly_points", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tavern_id"], ["taverns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "tavern_id", name="uq_player_tavern_state_player_tavern"),
    )
    op.create_index(
        "ix_player_tavern_state_player_id", "player_tavern_state", ["player_id"], unique=False
    )
    op.create_index(
        "ix_player_tavern_state_tavern_id", "player_tavern_state", ["tavern_id"], unique=False
    )

    op.create_table(
        "tavern_contributions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("player_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tavern_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tavern_id"], ["taverns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tavern_contributions_player_id", "tavern_contributions", ["player_id"], unique=False
    )
    op.create_index(
        "ix_tavern_contributions_tavern_id", "tavern_contributions", ["tavern_id"], unique=False
    )

    op.create_table(
        "parties",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tavern_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_by_player_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tavern_id"], ["taverns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_parties_created_by_player_id", "parties", ["created_by_player_id"], unique=False
    )
    op.create_index("ix_parties_tavern_id", "parties", ["tavern_id"], unique=False)

    op.create_table(
        "party_members",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("party_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("player_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "role_id", sa.String(length=64), nullable=False, server_default=sa.text("'vanguard'")
        ),
        sa.Column("loadout_skill_ids", sa.String(length=512), nullable=False),
        sa.Column("is_raid_lead", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("party_id", "player_id", name="uq_party_members_party_player"),
    )
    op.create_index("ix_party_members_party_id", "party_members", ["party_id"], unique=False)
    op.create_index("ix_party_members_player_id", "party_members", ["player_id"], unique=False)

    op.create_table(
        "raids",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("party_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("raid_template_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raids_party_id", "raids", ["party_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_raids_party_id", table_name="raids")
    op.drop_table("raids")

    op.drop_index("ix_party_members_player_id", table_name="party_members")
    op.drop_index("ix_party_members_party_id", table_name="party_members")
    op.drop_table("party_members")

    op.drop_index("ix_parties_tavern_id", table_name="parties")
    op.drop_index("ix_parties_created_by_player_id", table_name="parties")
    op.drop_table("parties")

    op.drop_index("ix_tavern_contributions_tavern_id", table_name="tavern_contributions")
    op.drop_index("ix_tavern_contributions_player_id", table_name="tavern_contributions")
    op.drop_table("tavern_contributions")

    op.drop_index("ix_player_tavern_state_tavern_id", table_name="player_tavern_state")
    op.drop_index("ix_player_tavern_state_player_id", table_name="player_tavern_state")
    op.drop_table("player_tavern_state")

    op.drop_index("ix_taverns_slug", table_name="taverns")
    op.drop_table("taverns")
