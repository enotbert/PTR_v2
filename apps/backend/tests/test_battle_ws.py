from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.identity import Player, PlayerSession
from app.models.tavern import TavernContribution
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


def _rl_command(command_id: str, room_id: str, *, target_entity: str | None) -> dict[str, object]:
    payload: dict[str, object] = {"command_id": command_id}
    if target_entity:
        payload["target"] = {"kind": "entity", "entity_id": target_entity}
    return {
        "protocol": "ptr.ws.v1",
        "kind": "command",
        "type": "combat.send_raid_lead_command",
        "room": {"kind": "battle", "id": room_id},
        "client_command_id": f"cmd-rl-{command_id}",
        "sent_at": "2026-05-05T18:05:00.000Z",
        "payload": payload,
    }


def _emoji(emoji_id: str, room_id: str, cmd_suffix: str) -> dict[str, object]:
    return {
        "protocol": "ptr.ws.v1",
        "kind": "command",
        "type": "combat.send_emoji",
        "room": {"kind": "battle", "id": room_id},
        "client_command_id": f"cmd-e-{cmd_suffix}",
        "sent_at": "2026-05-05T18:05:01.000Z",
        "payload": {"emoji_id": emoji_id},
    }


def _phrase(phrase_id: str, room_id: str, cmd_suffix: str) -> dict[str, object]:
    return {
        "protocol": "ptr.ws.v1",
        "kind": "command",
        "type": "combat.send_quick_phrase",
        "room": {"kind": "battle", "id": room_id},
        "client_command_id": f"cmd-q-{cmd_suffix}",
        "sent_at": "2026-05-05T18:05:02.000Z",
        "payload": {"phrase_id": phrase_id},
    }


def _finalize_raid(
    room_id: str, cmd_suffix: str, approve_failed_progress: bool
) -> dict[str, object]:
    return {
        "protocol": "ptr.ws.v1",
        "kind": "command",
        "type": "combat.finalize_raid",
        "room": {"kind": "battle", "id": room_id},
        "client_command_id": f"cmd-fr-{cmd_suffix}",
        "sent_at": "2026-05-05T18:05:03.000Z",
        "payload": {"approve_failed_progress": approve_failed_progress},
    }


def test_battle_ws_raid_lead_command_broadcasts_and_snapshots_mark(
    session_client: TestClient,
    db_session,
) -> None:
    _, owner_session = _make_player_with_session(db_session, "RLLeader")
    _, joiner_session = _make_player_with_session(db_session, "JoinerFan")
    db_session.commit()
    room_id = _create_party(session_client, owner_session, "vanguard")
    _join_party(session_client, room_id, joiner_session, "signal_bard")

    leader_path = f"/v1/ws/battles/{room_id}?session_id={owner_session}"
    joiner_path = f"/v1/ws/battles/{room_id}?session_id={joiner_session}"
    with (
        session_client.websocket_connect(leader_path) as ws_lead,
        session_client.websocket_connect(joiner_path) as ws_join,
    ):
        ws_lead.receive_json()
        ws_join.receive_json()

        ws_lead.send_json(
            _rl_command(
                "focus_target",
                room_id,
                target_entity="enemy:signal_leech",
            ),
        )
        ev_lead = ws_lead.receive_json()
        res_lead = ws_lead.receive_json()
        ev_join = ws_join.receive_json()

        assert ev_lead["type"] == "battle.event"
        assert ev_lead["payload"]["event_type"] == "raid_lead_command_sent"
        assert ev_lead["payload"]["command_id"] == "focus_target"
        assert ev_join["payload"]["target"]["entity_id"] == "enemy:signal_leech"
        assert res_lead["type"] == "command.result"

    with session_client.websocket_connect(leader_path) as ws2:
        snap = ws2.receive_json()
        assert snap["payload"]["last_raid_lead_command"] is not None
        assert snap["payload"]["last_raid_lead_command"]["command_id"] == "focus_target"

    with session_client.websocket_connect(joiner_path) as ws3:
        snap_j = ws3.receive_json()
        assert snap_j["payload"]["last_raid_lead_command"]["target"]["entity_id"] == (
            "enemy:signal_leech"
        )


def test_battle_ws_non_lead_raids_command_denied(session_client: TestClient, db_session) -> None:
    _, owner_session = _make_player_with_session(db_session, "RLCap")
    joiner_pid, joiner_session = _make_player_with_session(db_session, "Pleb")
    db_session.commit()
    room_id = _create_party(session_client, owner_session, "vanguard")
    _join_party(session_client, room_id, joiner_session, "signal_bard")
    joiner_actor = f"player:{joiner_pid}"

    joiner_path = f"/v1/ws/battles/{room_id}?session_id={joiner_session}"
    with session_client.websocket_connect(joiner_path) as ws:
        ws.receive_json()
        ws.send_json(
            _command(
                command_id="warmup",
                room_id=room_id,
                actor_id=joiner_actor,
                skill_id="signal_shot",
                target_id="enemy:rustbound_striker",
            ),
        )
        ws.receive_json()
        ws.receive_json()

        ws.send_json(_rl_command("rally", room_id, target_entity=None))
        err = ws.receive_json()
        assert err["type"] == "command.error"
        assert err["payload"]["code"] == "NOT_RAID_LEAD"


def test_battle_ws_emoji_and_phrase_broadcast(session_client: TestClient, db_session) -> None:
    owner_id, owner_session = _make_player_with_session(db_session, "EmojiSender")
    _, join_session = _make_player_with_session(db_session, "EmojiWatcher")
    db_session.commit()
    room_id = _create_party(session_client, owner_session, "vanguard")
    _join_party(session_client, room_id, join_session, "signal_bard")

    owner_path = f"/v1/ws/battles/{room_id}?session_id={owner_session}"
    join_path = f"/v1/ws/battles/{room_id}?session_id={join_session}"
    with (
        session_client.websocket_connect(owner_path) as ws_own,
        session_client.websocket_connect(join_path) as ws_watch,
    ):
        ws_own.receive_json()
        ws_watch.receive_json()

        ws_own.send_json(_emoji("nice", room_id, "1"))
        ev_o = ws_own.receive_json()
        res_o = ws_own.receive_json()
        ev_w = ws_watch.receive_json()
        assert ev_o["payload"]["event_type"] == "emoji_sent"
        assert ev_w["payload"]["emoji_id"] == "nice"
        assert res_o["payload"]["status"] == "accepted"

        ws_own.send_json(_phrase("need_heal", room_id, "2"))
        phrase_ev_o = ws_own.receive_json()
        phrase_res_o = ws_own.receive_json()
        phrase_ev_w = ws_watch.receive_json()
        assert phrase_ev_o["payload"]["event_type"] == "quick_phrase_sent"
        assert phrase_ev_w["payload"]["phrase_id"] == "need_heal"
        assert phrase_res_o["payload"]["status"] == "accepted"


def test_battle_ws_rate_limits_emoji_burst(session_client: TestClient, db_session) -> None:
    _, owner_session = _make_player_with_session(db_session, "SpamEmoji")
    db_session.commit()
    room_id = _create_party(session_client, owner_session, "vanguard")
    path = f"/v1/ws/battles/{room_id}?session_id={owner_session}"
    with session_client.websocket_connect(path) as ws:
        ws.receive_json()
        ws.send_json(_emoji("help", room_id, "a"))
        ws.receive_json()
        ws.receive_json()
        ws.send_json(_emoji("danger", room_id, "b"))
        limited = ws.receive_json()
        assert limited["type"] == "command.error"
        assert limited["payload"]["code"] == "RATE_LIMITED"
        assert limited["payload"]["retryable"] is True


def test_battle_ws_unsupported_command_type(session_client: TestClient, db_session) -> None:
    _, session_id = _make_player_with_session(db_session, "BadProto")
    db_session.commit()
    room_id = _create_party(session_client, session_id, "vanguard")
    ws_path = f"/v1/ws/battles/{room_id}?session_id={session_id}"
    with session_client.websocket_connect(ws_path) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "protocol": "ptr.ws.v1",
                "kind": "command",
                "type": "combat.unknown_proto",
                "room": {"kind": "battle", "id": room_id},
                "client_command_id": "unsupported-1",
                "sent_at": "2026-05-05T18:06:00.000Z",
                "payload": {},
            },
        )
        err = ws.receive_json()
        assert err["type"] == "command.error"
        assert err["payload"]["code"] == "UNSUPPORTED_PROTOCOL"


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


def test_battle_ws_finalize_raid_issues_rewards_and_persists_contributions(
    session_client: TestClient, db_session
) -> None:
    owner_id, owner_session = _make_player_with_session(db_session, "RaidLead")
    joiner_id, joiner_session = _make_player_with_session(db_session, "RaidJoiner")
    db_session.commit()
    room_id = _create_party(session_client, owner_session, "vanguard")
    _join_party(session_client, room_id, joiner_session, "signal_bard")
    actor_id = f"player:{owner_id}"

    owner_path = f"/v1/ws/battles/{room_id}?session_id={owner_session}"
    with session_client.websocket_connect(owner_path) as ws_owner:
        ws_owner.receive_json()
        strike_plan = (
            ("enemy:rustbound_striker", 8),
            ("enemy:signal_leech", 8),
            ("enemy:circuit_mender", 8),
            ("enemy:route_warden", 12),
        )
        cmd_idx = 0
        for target_enemy, hits in strike_plan:
            for _ in range(hits):
                ws_owner.send_json(
                    _command(
                        command_id=f"cmd-kill-{cmd_idx}",
                        room_id=room_id,
                        actor_id=actor_id,
                        skill_id="vanguard_strike",
                        target_id=target_enemy,
                    )
                )
                ws_owner.receive_json()
                ws_owner.receive_json()
                ws_owner.send_json(
                    _command(
                        command_id=f"cmd-fill-{cmd_idx}",
                        room_id=room_id,
                        actor_id=actor_id,
                        skill_id="mend_protocol",
                        target_id=actor_id,
                    )
                )
                ws_owner.receive_json()
                ws_owner.receive_json()
                cmd_idx += 1

        ws_owner.send_json(_finalize_raid(room_id, "ok", approve_failed_progress=False))
        event_owner = ws_owner.receive_json()
        result_owner = ws_owner.receive_json()
        assert event_owner["payload"]["event_type"] == "raid_outcome_resolved"
        assert event_owner["payload"]["status"] == "completed"
        assert event_owner["payload"]["reward_points_per_member"] == 30
        assert result_owner["payload"]["status"] == "accepted"

    rows = (
        db_session.query(TavernContribution)
        .filter(TavernContribution.source_type == "raid_reward")
        .all()
    )
    rewarded_players = {row.player_id for row in rows}
    assert owner_id in rewarded_players
    assert joiner_id in rewarded_players


def test_battle_ws_finalize_raid_rejects_non_final_outcome_without_approval(
    session_client: TestClient, db_session
) -> None:
    player_id, session_id = _make_player_with_session(db_session, "RaidNotDone")
    db_session.commit()
    room_id = _create_party(session_client, session_id, "vanguard")
    path = f"/v1/ws/battles/{room_id}?session_id={session_id}"
    with session_client.websocket_connect(path) as ws:
        ws.receive_json()
        ws.send_json(_finalize_raid(room_id, "blocked", approve_failed_progress=False))
        err = ws.receive_json()
        assert err["type"] == "command.error"
        assert err["payload"]["code"] == "OUTCOME_NOT_FINAL"

        ws.send_json(_finalize_raid(room_id, "approved", approve_failed_progress=True))
        event = ws.receive_json()
        result = ws.receive_json()
        assert event["type"] == "battle.event"
        assert event["payload"]["status"] == "failed"
        assert event["payload"]["reward_points_per_member"] == 10
        assert result["payload"]["status"] == "accepted"

    rows = (
        db_session.query(TavernContribution)
        .filter(TavernContribution.source_type == "raid_reward")
        .all()
    )
    assert any(row.player_id == player_id and row.amount == 10 for row in rows)
