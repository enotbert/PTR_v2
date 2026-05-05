from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.identity import Player, PlayerSession
from fastapi.testclient import TestClient


def _make_player_with_session(db_session, name: str) -> tuple[uuid.UUID, uuid.UUID]:
    now = datetime.now(UTC)
    player = Player(
        display_name=name,
        created_at=now,
        updated_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add(player)
    db_session.flush()
    session = PlayerSession(
        player_id=player.id,
        issued_at=now,
        expires_at=now + timedelta(days=30),
    )
    db_session.add(session)
    db_session.flush()
    return player.id, session.id


def _create_party(client: TestClient, session_id: uuid.UUID, role_id: str) -> str:
    created = client.post(
        "/v1/parties",
        headers={"Authorization": f"Bearer {session_id}"},
        json={"tavern_id": str(uuid.uuid4()), "role_id": role_id},
    )
    assert created.status_code == 200
    return created.json()["id"]


def _command(
    command_id: str, room_id: str, actor_id: str, skill_id: str, target_id: str
) -> dict[str, object]:
    return {
        "protocol": "ptr.ws.v1",
        "kind": "command",
        "type": "combat.use_skill",
        "room": {"kind": "battle", "id": room_id},
        "client_command_id": command_id,
        "sent_at": "2026-05-05T18:00:00.000Z",
        "payload": {
            "skill_id": skill_id,
            "actor_entity_id": actor_id,
            "target": {"kind": "entity", "entity_id": target_id},
        },
    }


def test_battle_ws_valid_path_emits_event_and_result(
    session_client: TestClient, db_session
) -> None:
    player_id, session_id = _make_player_with_session(db_session, "BattleOwner")
    db_session.commit()
    room_id = _create_party(session_client, session_id, "vanguard")
    actor_id = f"player:{player_id}"
    with session_client.websocket_connect(
        f"/v1/ws/battles/{room_id}?session_id={session_id}"
    ) as ws:
        snapshot = ws.receive_json()
        assert snapshot["type"] == "battle.snapshot"
        ws.send_json(
            _command(
                command_id="cmd-valid",
                room_id=room_id,
                actor_id=actor_id,
                skill_id="vanguard_strike",
                target_id="enemy:rustbound_striker",
            )
        )
        event = ws.receive_json()
        result = ws.receive_json()
        assert event["type"] == "battle.event"
        assert event["payload"]["event_type"] == "skill_resolved"
        assert result["type"] == "command.result"
        assert result["payload"]["status"] == "accepted"


def test_battle_ws_invalid_target_and_cooldown(session_client: TestClient, db_session) -> None:
    player_id, session_id = _make_player_with_session(db_session, "BattleInvalid")
    db_session.commit()
    room_id = _create_party(session_client, session_id, "vanguard")
    actor_id = f"player:{player_id}"
    with session_client.websocket_connect(
        f"/v1/ws/battles/{room_id}?session_id={session_id}"
    ) as ws:
        ws.receive_json()
        ws.send_json(
            _command(
                command_id="cmd-invalid",
                room_id=room_id,
                actor_id=actor_id,
                skill_id="vanguard_strike",
                target_id=actor_id,
            )
        )
        invalid = ws.receive_json()
        assert invalid["type"] == "command.error"
        assert invalid["payload"]["code"] == "INVALID_TARGET"

        ws.send_json(
            _command(
                command_id="cmd-cooldown-1",
                room_id=room_id,
                actor_id=actor_id,
                skill_id="vanguard_strike",
                target_id="enemy:rustbound_striker",
            )
        )
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            _command(
                command_id="cmd-cooldown-2",
                room_id=room_id,
                actor_id=actor_id,
                skill_id="vanguard_strike",
                target_id="enemy:rustbound_striker",
            )
        )
        cooldown = ws.receive_json()
        assert cooldown["type"] == "command.error"
        assert cooldown["payload"]["code"] == "COOLDOWN_ACTIVE"


def test_battle_ws_duplicate_and_conflict(session_client: TestClient, db_session) -> None:
    player_id, session_id = _make_player_with_session(db_session, "BattleDuplicate")
    db_session.commit()
    room_id = _create_party(session_client, session_id, "signal_bard")
    actor_id = f"player:{player_id}"
    with session_client.websocket_connect(
        f"/v1/ws/battles/{room_id}?session_id={session_id}"
    ) as ws:
        ws.receive_json()
        first = _command(
            command_id="cmd-dup",
            room_id=room_id,
            actor_id=actor_id,
            skill_id="signal_shot",
            target_id="enemy:rustbound_striker",
        )
        ws.send_json(first)
        ws.receive_json()
        ws.receive_json()

        ws.send_json(first)
        dup = ws.receive_json()
        assert dup["type"] == "command.result"
        assert dup["payload"]["status"] == "duplicate"

        conflict = _command(
            command_id="cmd-dup",
            room_id=room_id,
            actor_id=actor_id,
            skill_id="signal_shot",
            target_id="enemy:signal_leech",
        )
        ws.send_json(conflict)
        err = ws.receive_json()
        assert err["type"] == "command.error"
        assert err["payload"]["code"] == "IDEMPOTENCY_CONFLICT"
