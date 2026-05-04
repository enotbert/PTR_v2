"""Command idempotency row (v1 data model: command_dedup)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CommandDedup(Base):
    """One row per (player, room, client_command_id); prevents duplicate gameplay effects."""

    __tablename__ = "command_dedup"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "room_kind",
            "room_id",
            "client_command_id",
            name="uq_command_dedup_player_room_client",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    room_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    room_id: Mapped[str] = mapped_column(String(128), nullable=False)
    client_command_id: Mapped[str] = mapped_column(String(128), nullable=False)
    command_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    original_server_seq: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
