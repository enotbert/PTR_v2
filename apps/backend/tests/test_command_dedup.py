"""Tests for command idempotency (command_dedup)."""

from __future__ import annotations

import uuid

import pytest
from app.errors import ApiError
from app.services import command_dedup as cd


def test_canonical_payload_hash_stable() -> None:
    h1 = cd.canonical_payload_hash({"b": 1, "a": 2})
    h2 = cd.canonical_payload_hash({"a": 2, "b": 1})
    assert h1 == h2


def test_reserve_fresh_then_duplicate_same_hash(db_session, db_player_id: uuid.UUID) -> None:
    player_id = db_player_id
    h = cd.canonical_payload_hash({"x": 1})
    out1 = cd.reserve_command_dedup_slot(
        db_session,
        player_id=player_id,
        room_kind="battle",
        room_id="battle-1",
        client_command_id="cmd-1",
        command_type="combat_intent",
        payload_hash=h,
    )
    assert isinstance(out1, cd.CommandDedupFresh)
    out2 = cd.reserve_command_dedup_slot(
        db_session,
        player_id=player_id,
        room_kind="battle",
        room_id="battle-1",
        client_command_id="cmd-1",
        command_type="combat_intent",
        payload_hash=h,
    )
    assert isinstance(out2, cd.CommandDedupDuplicate)
    assert out2.row.id == out1.row.id
    d = cd.duplicate_command_details(out2.row)
    assert d["code"] == "duplicate_command"
    assert d["payload_hash"] == h
    assert d["in_flight"] is True


def test_conflict_different_payload_same_client_command_id(
    db_session,
    db_player_id: uuid.UUID,
) -> None:
    player_id = db_player_id
    h1 = cd.canonical_payload_hash({"x": 1})
    h2 = cd.canonical_payload_hash({"x": 2})
    cd.reserve_command_dedup_slot(
        db_session,
        player_id=player_id,
        room_kind="lobby",
        room_id="lobby-1",
        client_command_id="cmd-2",
        command_type="claim_reward",
        payload_hash=h1,
    )
    with pytest.raises(ApiError) as ei:
        cd.reserve_command_dedup_slot(
            db_session,
            player_id=player_id,
            room_kind="lobby",
            room_id="lobby-1",
            client_command_id="cmd-2",
            command_type="claim_reward",
            payload_hash=h2,
        )
    assert ei.value.status_code == 409
    assert ei.value.error == "command_id_conflict"
    assert ei.value.details is not None
    assert ei.value.details["expected_payload_hash"] == h1
    assert ei.value.details["provided_payload_hash"] == h2


def test_finalize_then_duplicate_shows_accepted(db_session, db_player_id: uuid.UUID) -> None:
    player_id = db_player_id
    h = cd.canonical_payload_hash({"move": "strike"})
    fresh = cd.reserve_command_dedup_slot(
        db_session,
        player_id=player_id,
        room_kind="battle",
        room_id="b9",
        client_command_id="cmd-3",
        command_type="combat_intent",
        payload_hash=h,
    )
    assert isinstance(fresh, cd.CommandDedupFresh)
    cd.finalize_command_dedup_accepted(db_session, fresh.row, original_server_seq=42)
    db_session.commit()
    dup = cd.reserve_command_dedup_slot(
        db_session,
        player_id=player_id,
        room_kind="battle",
        room_id="b9",
        client_command_id="cmd-3",
        command_type="combat_intent",
        payload_hash=h,
    )
    assert isinstance(dup, cd.CommandDedupDuplicate)
    assert dup.row.result_kind == cd.RESULT_ACCEPTED
    assert dup.row.original_server_seq == 42
    d = cd.duplicate_command_details(dup.row)
    assert d["in_flight"] is False


def test_mark_rejected_then_duplicate(db_session, db_player_id: uuid.UUID) -> None:
    player_id = db_player_id
    h = cd.canonical_payload_hash({})
    fresh = cd.reserve_command_dedup_slot(
        db_session,
        player_id=player_id,
        room_kind="battle",
        room_id="b1",
        client_command_id="cmd-4",
        command_type="combat_intent",
        payload_hash=h,
    )
    assert isinstance(fresh, cd.CommandDedupFresh)
    cd.mark_command_dedup_rejected(db_session, fresh.row)
    dup = cd.reserve_command_dedup_slot(
        db_session,
        player_id=player_id,
        room_kind="battle",
        room_id="b1",
        client_command_id="cmd-4",
        command_type="combat_intent",
        payload_hash=h,
    )
    assert isinstance(dup, cd.CommandDedupDuplicate)
    assert dup.row.result_kind == cd.RESULT_REJECTED
