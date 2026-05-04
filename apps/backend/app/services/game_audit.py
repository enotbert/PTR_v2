"""Append-only game audit events with conservative payload redaction."""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.game_audit_event import GameAuditEvent

_DENYLIST_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "authorization",
    "cookie",
    "set-cookie",
    "api_key",
    "apikey",
)


def _redact_value(key: str, value: Any) -> Any:
    lower = key.lower()
    if any(s in lower for s in _DENYLIST_SUBSTRINGS):
        return "[redacted]"
    return sanitize_audit_payload(value)


def sanitize_audit_payload(value: Any) -> Any:
    """Return a JSON-serializable structure safe for persisted audit logs."""

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                k = str(k)
            out[k] = _redact_value(k, v)
        return out
    if isinstance(value, list):
        return [sanitize_audit_payload(v) for v in value]
    if isinstance(value, str) and len(value) > 512:
        return value[:512] + "…"
    return value


def record_game_audit_event(
    db: Session,
    *,
    event_name: str,
    payload: dict[str, Any],
    player_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    event_at: datetime | None = None,
) -> GameAuditEvent:
    """Persist an audit record.

    ``payload`` is deep-copied and passed through ``sanitize_audit_payload``.
    """

    safe_payload = sanitize_audit_payload(copy.deepcopy(payload))
    row = GameAuditEvent(
        player_id=player_id,
        session_id=session_id,
        event_name=event_name,
        payload_json=safe_payload,
        event_at=event_at or datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    return row
