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


def _create_party(client: TestClient, session_id: uuid.UUID) -> str:
    tavern_id = uuid.uuid4()
    created = client.post(
        "/v1/parties",
        headers={"Authorization": f"Bearer {session_id}"},
        json={"tavern_id": str(tavern_id), "role_id": "vanguard"},
    )
    assert created.status_code == 200
    return created.json()["id"]


def test_lobby_ws_snapshot_event_and_result(session_client: TestClient, db_session) -> None:
    _, owner_session_id = _make_player_with_session(db_session, "OwnerWs")
    db_session.commit()
    party_id = _create_party(session_client, owner_session_id)

    with session_client.websocket_connect(
        f"/v1/ws/lobbies/{party_id}?session_id={owner_session_id}"
    ) as ws:
        snapshot = ws.receive_json()
        assert snapshot["type"] == "lobby.snapshot"
        assert snapshot["kind"] == "snapshot"
        assert snapshot["payload"]["lobby_id"] == party_id
        assert snapshot["payload"]["players"][0]["status"] == "not_ready"

        ws.send_json(
            {
                "protocol": "ptr.ws.v1",
                "kind": "command",
                "type": "lobby.set_player_status",
                "room": {"kind": "lobby", "id": party_id},
                "client_command_id": "cmd-1",
                "sent_at": "2026-05-05T18:00:00.000Z",
                "payload": {"status": "ready"},
            }
        )
        event = ws.receive_json()
        result = ws.receive_json()
        assert event["type"] == "lobby.event"
        assert event["payload"]["event_type"] == "player_status_changed"
        assert event["payload"]["status"] == "ready"
        assert result["type"] == "command.result"
        assert result["payload"]["status"] == "accepted"
        assert result["payload"]["applied_server_seq"] == event["server_seq"]


def test_lobby_ws_reconnect_gets_fresh_snapshot(session_client: TestClient, db_session) -> None:
    _, owner_session_id = _make_player_with_session(db_session, "ReconnectOwner")
    db_session.commit()
    party_id = _create_party(session_client, owner_session_id)

    with session_client.websocket_connect(
        f"/v1/ws/lobbies/{party_id}?session_id={owner_session_id}"
    ) as ws1:
        first_snapshot = ws1.receive_json()
        ws1.send_json(
            {
                "protocol": "ptr.ws.v1",
                "kind": "command",
                "type": "lobby.set_player_status",
                "room": {"kind": "lobby", "id": party_id},
                "client_command_id": "cmd-reconnect",
                "sent_at": "2026-05-05T18:00:00.000Z",
                "payload": {"status": "ready"},
            }
        )
        ws1.receive_json()
        ws1.receive_json()

    with session_client.websocket_connect(
        f"/v1/ws/lobbies/{party_id}?session_id={owner_session_id}"
    ) as ws2:
        second_snapshot = ws2.receive_json()
        assert second_snapshot["type"] == "lobby.snapshot"
        assert second_snapshot["server_seq"] > first_snapshot["server_seq"]
        assert second_snapshot["payload"]["players"][0]["status"] == "ready"
