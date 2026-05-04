"""Business logic for anonymous player sessions (v1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models.identity import Player, PlayerSession

SESSION_TTL = timedelta(days=30)
DEFAULT_DISPLAY_NAME = "Adventurer"


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(dt: datetime) -> datetime:
    """SQLite may return naive datetimes; normalize for comparisons."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def normalize_display_name(raw: str | None) -> str:
    name = (raw or "").strip()
    if not name:
        return DEFAULT_DISPLAY_NAME
    return name[:64]


def create_new_session(
    db: Session,
    *,
    display_name: str | None,
    device_fingerprint: str | None,
    last_ip: str | None,
    last_user_agent: str | None,
) -> tuple[Player, PlayerSession]:
    now = _now()
    player = Player(
        display_name=normalize_display_name(display_name),
        created_at=now,
        updated_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db.add(player)
    db.flush()
    row = PlayerSession(
        player_id=player.id,
        device_fingerprint=device_fingerprint,
        issued_at=now,
        expires_at=now + SESSION_TTL,
        last_ip=last_ip,
        last_user_agent=last_user_agent,
    )
    db.add(row)
    db.flush()
    return player, row


def get_session_by_id(db: Session, session_id: uuid.UUID) -> PlayerSession | None:
    return db.get(PlayerSession, session_id)


def validate_and_touch_session(
    db: Session,
    row: PlayerSession,
    *,
    last_ip: str | None,
    last_user_agent: str | None,
) -> tuple[Player, PlayerSession]:
    now = _now()
    if row.revoked_at is not None:
        raise ApiError(
            status_code=401,
            error="session_revoked",
            message="Session has been revoked.",
        )
    if _as_utc(row.expires_at) <= now:
        raise ApiError(
            status_code=401,
            error="session_expired",
            message="Session has expired.",
        )
    player = row.player
    player.last_seen_at = now
    player.updated_at = now
    row.expires_at = now + SESSION_TTL
    row.last_ip = last_ip
    row.last_user_agent = last_user_agent
    db.add(player)
    db.add(row)
    return player, row


def resume_session(
    db: Session,
    session_id: uuid.UUID,
    *,
    last_ip: str | None,
    last_user_agent: str | None,
) -> tuple[Player, PlayerSession]:
    row = get_session_by_id(db, session_id)
    if row is None:
        raise ApiError(
            status_code=404,
            error="session_not_found",
            message="Session was not found.",
        )
    return validate_and_touch_session(db, row, last_ip=last_ip, last_user_agent=last_user_agent)
