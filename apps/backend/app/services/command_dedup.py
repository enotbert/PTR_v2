"""Idempotent client command handling (command_dedup table).

Rows use ``result_kind='pending'`` until the server finalizes ``accepted``/``rejected``.
Production Postgres DDL must match these models (Alembic migration is maintained separately).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models.command_dedup import CommandDedup

RESULT_PENDING = "pending"
RESULT_ACCEPTED = "accepted"
RESULT_REJECTED = "rejected"

DEDUP_DEFAULT_TTL = timedelta(days=30)


def _now() -> datetime:
    return datetime.now(UTC)


def canonical_payload_hash(payload: Any) -> str:
    """Stable SHA-256 over canonical JSON (sorted keys)."""

    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CommandDedupFresh:
    row: CommandDedup


@dataclass(frozen=True)
class CommandDedupDuplicate:
    row: CommandDedup


def duplicate_command_details(row: CommandDedup) -> dict[str, Any]:
    """Structured fields for HTTP/WS responses (no secrets)."""

    return {
        "code": "duplicate_command",
        "client_command_id": row.client_command_id,
        "command_type": row.command_type,
        "payload_hash": row.payload_hash,
        "result_kind": row.result_kind,
        "original_server_seq": row.original_server_seq,
        "in_flight": row.result_kind == RESULT_PENDING,
    }


def _load_existing(
    db: Session,
    *,
    player_id: uuid.UUID,
    room_kind: str,
    room_id: str,
    client_command_id: str,
) -> CommandDedup | None:
    return db.scalar(
        select(CommandDedup).where(
            CommandDedup.player_id == player_id,
            CommandDedup.room_kind == room_kind,
            CommandDedup.room_id == room_id,
            CommandDedup.client_command_id == client_command_id,
        )
    )


def reserve_command_dedup_slot(
    db: Session,
    *,
    player_id: uuid.UUID,
    room_kind: str,
    room_id: str,
    client_command_id: str,
    command_type: str,
    payload_hash: str,
    now: datetime | None = None,
    expires_at: datetime | None = None,
) -> CommandDedupFresh | CommandDedupDuplicate:
    """Reserve idempotency slot before applying a gameplay side effect.

    Returns ``CommandDedupDuplicate`` when the same client command id was already seen
    with the same payload hash (caller must not re-apply the effect).
    Raises ``ApiError`` (409) when the same client command id is reused with a different payload.
    """

    ts = now or _now()
    exp = expires_at or (ts + DEDUP_DEFAULT_TTL)
    row = CommandDedup(
        player_id=player_id,
        room_kind=room_kind,
        room_id=room_id,
        client_command_id=client_command_id,
        command_type=command_type,
        payload_hash=payload_hash,
        result_kind=RESULT_PENDING,
        original_server_seq=None,
        created_at=ts,
        expires_at=exp,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        existing = _load_existing(
            db,
            player_id=player_id,
            room_kind=room_kind,
            room_id=room_id,
            client_command_id=client_command_id,
        )
        if existing is None:
            raise ApiError(
                status_code=409,
                error="command_dedup_race",
                message="Command deduplication state could not be resolved; retry.",
            ) from None
        if existing.payload_hash != payload_hash:
            raise ApiError(
                status_code=409,
                error="command_id_conflict",
                message="The same client_command_id was reused with a different payload.",
                details={
                    "code": "command_id_conflict",
                    "client_command_id": client_command_id,
                    "expected_payload_hash": existing.payload_hash,
                    "provided_payload_hash": payload_hash,
                },
            ) from None
        return CommandDedupDuplicate(row=existing)
    return CommandDedupFresh(row=row)


def finalize_command_dedup_accepted(
    db: Session,
    row: CommandDedup,
    *,
    original_server_seq: int,
) -> None:
    """Mark a previously reserved row as accepted with authoritative server sequence."""

    if row.result_kind != RESULT_PENDING:
        msg = "Command dedup row is not pending; cannot finalize as accepted."
        raise RuntimeError(msg)
    row.result_kind = RESULT_ACCEPTED
    row.original_server_seq = original_server_seq
    db.add(row)


def mark_command_dedup_rejected(db: Session, row: CommandDedup) -> None:
    """Mark a reserved row as rejected (validation failed or dropped command)."""

    if row.result_kind != RESULT_PENDING:
        msg = "Command dedup row is not pending; cannot mark rejected."
        raise RuntimeError(msg)
    row.result_kind = RESULT_REJECTED
    db.add(row)
