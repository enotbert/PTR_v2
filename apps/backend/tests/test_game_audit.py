"""Tests for game audit payload redaction and persistence."""

from __future__ import annotations

import uuid

from app.models.game_audit_event import GameAuditEvent
from app.services import game_audit as ga


def test_sanitize_audit_payload_redacts_nested_secrets() -> None:
    raw = {
        "action": "reward_claim",
        "nested": {"api_key": "super-secret", "ok": 1},
        "Authorization": "bearer x",
    }
    safe = ga.sanitize_audit_payload(raw)
    assert safe["nested"]["api_key"] == "[redacted]"
    assert safe["nested"]["ok"] == 1
    assert safe["Authorization"] == "[redacted]"
    assert safe["action"] == "reward_claim"


def test_record_game_audit_event_truncates_long_strings(db_session) -> None:
    long = "a" * 600
    row = ga.record_game_audit_event(
        db_session,
        event_name="combat_intent",
        payload={"note": long},
    )
    assert isinstance(row, GameAuditEvent)
    stored = row.payload_json["note"]
    assert isinstance(stored, str)
    assert len(stored) <= 514
    assert stored.endswith("…")


def test_record_game_audit_with_player_and_session(
    db_session, db_player_session_ids: tuple[uuid.UUID, uuid.UUID]
) -> None:
    player_id, session_id = db_player_session_ids
    row = ga.record_game_audit_event(
        db_session,
        event_name="reward_claim_decision",
        payload={"reward_id": str(uuid.uuid4()), "outcome": "granted"},
        player_id=player_id,
        session_id=session_id,
    )
    assert row.player_id == player_id
    assert row.session_id == session_id
