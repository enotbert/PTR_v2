"""WebSocket battle room endpoint (PTR-40)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.api.deps import parse_bearer_session_id
from app.db import get_db
from app.errors import ApiError
from app.models.party_raid import Party, PartyMember
from app.services import combat_engine, game_audit
from app.services import command_dedup as dedup_service
from app.services.session import assert_active_session_player_id

router = APIRouter()

PROTOCOL = "ptr.ws.v1"
ROOM_KIND = "battle"


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_ws_session_id(websocket: WebSocket) -> uuid.UUID:
    raw_auth = websocket.headers.get("authorization")
    from_bearer = parse_bearer_session_id(raw_auth)
    if from_bearer is not None:
        return from_bearer
    from_query = websocket.query_params.get("session_id", "").strip()
    if from_query:
        try:
            return uuid.UUID(from_query)
        except ValueError:
            pass
    raise ApiError(
        status_code=401,
        error="missing_authorization",
        message="Provide Authorization bearer token or ?session_id=UUID.",
    )


@dataclass
class BattleRoom:
    state: combat_engine.BattleRoomState
    entities: dict[str, combat_engine.BattleSnapshotEntity]
    entity_teams: dict[str, str]
    player_actor_map: dict[str, str]


class BattleWsStore:
    def __init__(self) -> None:
        self._rooms: dict[str, BattleRoom] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, room_id: str, create_from_party: list[PartyMember]) -> BattleRoom:
        async with self._lock:
            existing = self._rooms.get(room_id)
            if existing is not None:
                return existing
            entities: dict[str, combat_engine.BattleSnapshotEntity] = {}
            entity_teams: dict[str, str] = {}
            player_actor_map: dict[str, str] = {}
            for member in create_from_party:
                entity_id = f"player:{member.player_id}"
                entities[entity_id] = combat_engine.BattleSnapshotEntity(
                    entity_id=entity_id,
                    kind="player",
                    hp_current=100,
                    hp_max=100,
                    role_id=member.role_id,
                )
                entity_teams[entity_id] = "ally"
                player_actor_map[str(member.player_id)] = entity_id

            for enemy_id in (
                "enemy:rustbound_striker",
                "enemy:signal_leech",
                "enemy:circuit_mender",
                "enemy:route_warden",
            ):
                kind = "boss" if enemy_id.endswith("route_warden") else "enemy"
                entities[enemy_id] = combat_engine.BattleSnapshotEntity(
                    entity_id=enemy_id,
                    kind=kind,
                    hp_current=120 if kind == "boss" else 80,
                    hp_max=120 if kind == "boss" else 80,
                )
                entity_teams[enemy_id] = "enemy"

            room = BattleRoom(
                state=combat_engine.BattleRoomState(),
                entities=entities,
                entity_teams=entity_teams,
                player_actor_map=player_actor_map,
            )
            self._rooms[room_id] = room
            return room


STORE = BattleWsStore()


def _load_party_membership(
    db: Session, battle_id: uuid.UUID, player_id: uuid.UUID
) -> tuple[Party, list[PartyMember]]:
    party = db.get(Party, battle_id)
    if party is None:
        raise ApiError(status_code=404, error="room_not_found", message="Battle was not found.")
    stmt: Select[tuple[PartyMember]] = select(PartyMember).where(
        PartyMember.party_id == battle_id,
        PartyMember.left_at.is_(None),
    )
    members = list(db.execute(stmt).scalars().all())
    if not any(member.player_id == player_id for member in members):
        raise ApiError(
            status_code=403,
            error="room_forbidden",
            message="Player is not in this battle room.",
        )
    return party, members


def _result_message(
    *,
    room_id: str,
    server_seq: int,
    client_command_id: str,
    status_value: str,
    applied_server_seq: int | None,
    original_server_seq: int | None,
) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "kind": "result",
        "type": "command.result",
        "room": {"kind": ROOM_KIND, "id": room_id},
        "server_seq": server_seq,
        "client_command_id": client_command_id,
        "sent_at": _iso_now(),
        "payload": {
            "status": status_value,
            "command_type": "combat.use_skill",
            "applied_server_seq": applied_server_seq,
            "original_server_seq": original_server_seq,
        },
    }


def _error_message(
    *,
    room_id: str,
    server_seq: int,
    client_command_id: str,
    code: str,
    reason: str,
    retryable: bool,
    original_server_seq: int | None = None,
) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "kind": "error",
        "type": "command.error",
        "room": {"kind": ROOM_KIND, "id": room_id},
        "server_seq": server_seq,
        "client_command_id": client_command_id,
        "sent_at": _iso_now(),
        "payload": {
            "command_type": "combat.use_skill",
            "code": code,
            "reason": reason,
            "retryable": retryable,
            "original_server_seq": original_server_seq,
        },
    }


def _snapshot(
    room_id: str,
    lobby_id: str,
    room: BattleRoom,
    raid_lead_player_id: str,
) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []
    for entity in room.entities.values():
        entities.append(
            {
                "entity_id": entity.entity_id,
                "kind": entity.kind,
                "hp": {"current": entity.hp_current, "max": entity.hp_max},
                "states": [],
                "effects": [],
                "skill_state": [],
                "target_hints": [],
                "role_id": entity.role_id,
            }
        )
    return {
        "protocol": PROTOCOL,
        "kind": "snapshot",
        "type": "battle.snapshot",
        "room": {"kind": ROOM_KIND, "id": room_id},
        "server_seq": room.state.issue_server_seq(),
        "sent_at": _iso_now(),
        "payload": {
            "battle_id": room_id,
            "lobby_id": lobby_id,
            "phase": room.state.phase,
            "party_order": [
                entity_id for entity_id, team in room.entity_teams.items() if team == "ally"
            ],
            "raid_lead_player_id": raid_lead_player_id,
            "entities": entities,
            "links": [],
            "last_raid_lead_command": None,
            "result": None,
        },
    }


@router.websocket("/ws/battles/{battle_id}")
async def battle_room_ws(
    websocket: WebSocket,
    battle_id: str,
    db: Session = Depends(get_db),  # noqa: B008 - FastAPI dependency injection pattern
) -> None:
    await websocket.accept()
    try:
        battle_uuid = uuid.UUID(battle_id)
        session_id = _parse_ws_session_id(websocket)
        player_id = assert_active_session_player_id(db, session_id)
        party, members = _load_party_membership(db, battle_uuid, player_id)
    except ApiError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    room = await STORE.get_or_create(battle_id, members)
    raid_lead_player_id = str(
        next((m.player_id for m in members if m.is_raid_lead), members[0].player_id)
    )
    await websocket.send_json(_snapshot(battle_id, str(party.id), room, raid_lead_player_id))

    actor_entity_id = room.player_actor_map.get(str(player_id))
    if actor_entity_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    while True:
        try:
            message = await websocket.receive_json()
        except WebSocketDisconnect:
            break

        kind = message.get("kind")
        msg_type = message.get("type")
        command_id = str(message.get("client_command_id", "")).strip()
        payload = message.get("payload") or {}
        msg_room = message.get("room") or {}
        if (
            kind != "command"
            or msg_type != "combat.use_skill"
            or msg_room.get("kind") != ROOM_KIND
            or str(msg_room.get("id")) != battle_id
            or not command_id
        ):
            seq = room.state.issue_server_seq()
            await websocket.send_json(
                _error_message(
                    room_id=battle_id,
                    server_seq=seq,
                    client_command_id=command_id or "missing_command_id",
                    code="INVALID_PAYLOAD",
                    reason="Invalid command envelope.",
                    retryable=False,
                )
            )
            continue

        requested_actor_id = str(payload.get("actor_entity_id", "")).strip()
        if requested_actor_id != actor_entity_id:
            seq = room.state.issue_server_seq()
            await websocket.send_json(
                _error_message(
                    room_id=battle_id,
                    server_seq=seq,
                    client_command_id=command_id,
                    code="UNAUTHORIZED",
                    reason="Actor does not belong to current session.",
                    retryable=False,
                )
            )
            continue

        payload_hash = dedup_service.canonical_payload_hash(payload)
        try:
            dedup_result = dedup_service.reserve_command_dedup_slot(
                db,
                player_id=player_id,
                room_kind=ROOM_KIND,
                room_id=battle_id,
                client_command_id=command_id,
                command_type="combat.use_skill",
                payload_hash=payload_hash,
            )
        except ApiError:
            seq = room.state.issue_server_seq()
            await websocket.send_json(
                _error_message(
                    room_id=battle_id,
                    server_seq=seq,
                    client_command_id=command_id,
                    code="IDEMPOTENCY_CONFLICT",
                    reason="client_command_id was reused with another payload.",
                    retryable=False,
                )
            )
            continue

        if isinstance(dedup_result, dedup_service.CommandDedupDuplicate):
            seq = room.state.issue_server_seq()
            status_value = (
                "duplicate"
                if dedup_result.row.result_kind == dedup_service.RESULT_ACCEPTED
                else "accepted"
            )
            await websocket.send_json(
                _result_message(
                    room_id=battle_id,
                    server_seq=seq,
                    client_command_id=command_id,
                    status_value=status_value,
                    applied_server_seq=dedup_result.row.original_server_seq,
                    original_server_seq=dedup_result.row.original_server_seq,
                )
            )
            continue

        try:
            resolution = combat_engine.resolve_use_skill(
                payload=payload,
                actor_entity_id=actor_entity_id,
                actor_team="ally",
                valid_entity_teams=room.entity_teams,
                state=room.state,
            )
        except ValueError as exc:
            dedup_service.mark_command_dedup_rejected(db, dedup_result.row)
            db.commit()
            code = str(exc)
            seq = room.state.issue_server_seq()
            await websocket.send_json(
                _error_message(
                    room_id=battle_id,
                    server_seq=seq,
                    client_command_id=command_id,
                    code=code,
                    reason="Skill validation failed.",
                    retryable=False,
                )
            )
            continue
        except RuntimeError:
            dedup_service.mark_command_dedup_rejected(db, dedup_result.row)
            db.commit()
            seq = room.state.issue_server_seq()
            await websocket.send_json(
                _error_message(
                    room_id=battle_id,
                    server_seq=seq,
                    client_command_id=command_id,
                    code="COOLDOWN_ACTIVE",
                    reason="Skill cooldown is still active.",
                    retryable=False,
                )
            )
            continue

        event_seq = room.state.issue_server_seq()
        dedup_service.finalize_command_dedup_accepted(
            db, dedup_result.row, original_server_seq=event_seq
        )
        game_audit.record_game_audit_event(
            db,
            event_name="battle.skill_resolved",
            player_id=player_id,
            session_id=session_id,
            payload={
                "battle_id": battle_id,
                "command_type": "combat.use_skill",
                "client_command_id": command_id,
                "event_payload": resolution.event_payload,
            },
        )
        db.commit()
        await websocket.send_json(
            {
                "protocol": PROTOCOL,
                "kind": "event",
                "type": "battle.event",
                "room": {"kind": ROOM_KIND, "id": battle_id},
                "server_seq": event_seq,
                "sent_at": _iso_now(),
                "payload": resolution.event_payload,
            }
        )
        result_seq = room.state.issue_server_seq()
        await websocket.send_json(
            _result_message(
                room_id=battle_id,
                server_seq=result_seq,
                client_command_id=command_id,
                status_value="accepted",
                applied_server_seq=event_seq,
                original_server_seq=event_seq,
            )
        )
