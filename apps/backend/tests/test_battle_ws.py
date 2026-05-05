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


def _join_party(client: TestClient, party_id: str, session_id: uuid.UUID, role_id: str) -> None:
    joined = client.post(
        f"/v1/parties/{party_id}/join",
        headers={"Authorization": f"Bearer {session_id}"},
        json={"role_id": role_id},
    )
    assert joined.status_code == 200


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


def test_battle_ws_broadcasts_event_to_all_room_participants(
    session_client: TestClient, db_session
) -> None:
    owner_id, owner_session = _make_player_with_session(db_session, "BattleLeader")
    _, joiner_session = _make_player_with_session(db_session, "BattleJoiner")
    db_session.commit()
    room_id = _create_party(session_client, owner_session, "vanguard")
    _join_party(session_client, room_id, joiner_session, "signal_bard")
    actor_id = f"player:{owner_id}"

    owner_path = f"/v1/ws/battles/{room_id}?session_id={owner_session}"
    joiner_path = f"/v1/ws/battles/{room_id}?session_id={joiner_session}"
    with (
        session_client.websocket_connect(owner_path) as ws_owner,
        session_client.websocket_connect(joiner_path) as ws_joiner,
    ):
        ws_owner.receive_json()
        ws_joiner.receive_json()

        ws_owner.send_json(
            _command(
                command_id="cmd-broadcast",
                room_id=room_id,
                actor_id=actor_id,
                skill_id="vanguard_strike",
                target_id="enemy:rustbound_striker",
            )
        )

        owner_event = ws_owner.receive_json()
        owner_result = ws_owner.receive_json()
        joiner_event = ws_joiner.receive_json()
        assert owner_event["type"] == "battle.event"
        assert joiner_event["type"] == "battle.event"
        assert owner_event["server_seq"] == joiner_event["server_seq"]
        assert owner_result["type"] == "command.result"


def test_battle_ws_reconnect_receives_fresh_snapshot(
    session_client: TestClient, db_session
) -> None:
    player_id, session_id = _make_player_with_session(db_session, "BattleReconnect")
    db_session.commit()
    room_id = _create_party(session_client, session_id, "vanguard")
    actor_id = f"player:{player_id}"

    first_snapshot_seq = 0
    ws_path = f"/v1/ws/battles/{room_id}?session_id={session_id}"
    with session_client.websocket_connect(ws_path) as ws:
        first_snapshot = ws.receive_json()
        first_snapshot_seq = first_snapshot["server_seq"]
        ws.send_json(
            _command(
                command_id="cmd-before-reconnect",
                room_id=room_id,
                actor_id=actor_id,
                skill_id="vanguard_strike",
                target_id="enemy:rustbound_striker",
            )
        )
        ws.receive_json()
        ws.receive_json()

    with session_client.websocket_connect(ws_path) as ws_reconnect:
        reconnect_snapshot = ws_reconnect.receive_json()
        assert reconnect_snapshot["type"] == "battle.snapshot"
        assert reconnect_snapshot["server_seq"] > first_snapshot_seq
