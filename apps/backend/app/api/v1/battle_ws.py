"""WebSocket battle room endpoint (PTR-40, PTR-45)."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
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

RAID_LEAD_COMMAND_IDS = frozenset(
    {"focus_target", "interrupt_channel", "break_link", "hold_defense", "rally"},
)
TARGETED_RAID_LEAD_COMMAND_IDS = frozenset(
    {"focus_target", "interrupt_channel", "break_link"},
)

EMOJI_IDS = frozenset({"thumbs_up", "on_my_way", "danger", "nice", "help"})
QUICK_PHRASE_IDS = frozenset(
    {
        "need_heal",
        "shield_me",
        "focus_marked",
        "cooldown_ready",
        "good_job",
        "retreat",
    },
)

COMM_PULSE_MIN_INTERVAL_S = 0.4


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
    connections: set[WebSocket]
    raid_lead_player_id: str = ""
    last_raid_lead_command: dict[str, Any] | None = None
    comm_rate_last: dict[str, float] = field(default_factory=dict)


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
            raid_lead = next(
                (m for m in create_from_party if m.is_raid_lead),
                create_from_party[0],
            )
            raid_lead_player_id = str(raid_lead.player_id)
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
                connections=set(),
                raid_lead_player_id=raid_lead_player_id,
                last_raid_lead_command=None,
                comm_rate_last={},
            )
            self._rooms[room_id] = room
            return room

    async def add_connection(self, room_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(room_id)
            if room is not None:
                room.connections.add(websocket)

    async def remove_connection(self, room_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(room_id)
            if room is not None:
                room.connections.discard(websocket)

    async def room_connections(self, room_id: str) -> list[WebSocket]:
        async with self._lock:
            room = self._rooms.get(room_id)
            if room is None:
                return []
            return list(room.connections)

    async def is_comm_rate_limited(
        self,
        room_id: str,
        player_id: str,
        bucket: str,
        min_interval: float,
    ) -> bool:
        async with self._lock:
            room = self._rooms.get(room_id)
            if room is None:
                return True
            key = f"{player_id}:{bucket}"
            now = time.monotonic()
            last = room.comm_rate_last.get(key, 0.0)
            if now - last < min_interval:
                return True
            room.comm_rate_last[key] = now
            return False


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
    command_type: str,
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
            "command_type": command_type,
            "applied_server_seq": applied_server_seq,
            "original_server_seq": original_server_seq,
        },
    }


def _error_message(
    *,
    room_id: str,
    server_seq: int,
    client_command_id: str,
    command_type: str,
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
            "command_type": command_type,
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
            },
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
            "last_raid_lead_command": room.last_raid_lead_command,
            "result": None,
        },
    }


async def _broadcast_room_message(room_id: str, message: dict[str, Any]) -> None:
    disconnected: list[WebSocket] = []
    for ws in await STORE.room_connections(room_id):
        try:
            await ws.send_json(message)
        except RuntimeError:
            disconnected.append(ws)
    for ws in disconnected:
        await STORE.remove_connection(room_id, ws)


async def _send_command_error(
    websocket: WebSocket,
    *,
    battle_id: str,
    room: BattleRoom,
    client_command_id: str,
    command_type: str,
    code: str,
    reason: str,
    retryable: bool,
    original_server_seq: int | None = None,
) -> None:
    seq = room.state.issue_server_seq()
    await websocket.send_json(
        _error_message(
            room_id=battle_id,
            server_seq=seq,
            client_command_id=client_command_id,
            command_type=command_type,
            code=code,
            reason=reason,
            retryable=retryable,
            original_server_seq=original_server_seq,
        ),
    )


async def _handle_use_skill(
    websocket: WebSocket,
    *,
    battle_id: str,
    room: BattleRoom,
    db: Session,
    player_id: uuid.UUID,
    session_id: uuid.UUID,
    actor_entity_id: str,
    payload: dict[str, Any],
    client_command_id: str,
) -> None:
    command_type = "combat.use_skill"
    payload_hash = dedup_service.canonical_payload_hash(payload)
    try:
        dedup_result = dedup_service.reserve_command_dedup_slot(
            db,
            player_id=player_id,
            room_kind=ROOM_KIND,
            room_id=battle_id,
            client_command_id=client_command_id,
            command_type=command_type,
            payload_hash=payload_hash,
        )
    except ApiError:
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="IDEMPOTENCY_CONFLICT",
            reason="client_command_id was reused with another payload.",
            retryable=False,
        )
        return

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
                client_command_id=client_command_id,
                status_value=status_value,
                command_type=command_type,
                applied_server_seq=dedup_result.row.original_server_seq,
                original_server_seq=dedup_result.row.original_server_seq,
            ),
        )
        return

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
                client_command_id=client_command_id,
                command_type=command_type,
                code=code,
                reason="Skill validation failed.",
                retryable=False,
            ),
        )
        return
    except RuntimeError:
        dedup_service.mark_command_dedup_rejected(db, dedup_result.row)
        db.commit()
        seq = room.state.issue_server_seq()
        await websocket.send_json(
            _error_message(
                room_id=battle_id,
                server_seq=seq,
                client_command_id=client_command_id,
                command_type=command_type,
                code="COOLDOWN_ACTIVE",
                reason="Skill cooldown is still active.",
                retryable=False,
            ),
        )
        return

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
            "command_type": command_type,
            "client_command_id": client_command_id,
            "event_payload": resolution.event_payload,
        },
    )
    db.commit()
    await _broadcast_room_message(
        battle_id,
        {
            "protocol": PROTOCOL,
            "kind": "event",
            "type": "battle.event",
            "room": {"kind": ROOM_KIND, "id": battle_id},
            "server_seq": event_seq,
            "sent_at": _iso_now(),
            "payload": resolution.event_payload,
        },
    )
    result_seq = room.state.issue_server_seq()
    await websocket.send_json(
        _result_message(
            room_id=battle_id,
            server_seq=result_seq,
            client_command_id=client_command_id,
            status_value="accepted",
            command_type=command_type,
            applied_server_seq=event_seq,
            original_server_seq=event_seq,
        ),
    )


def _normalized_target(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("target")
    return raw if isinstance(raw, dict) else {}


async def _handle_send_raid_lead_command(
    websocket: WebSocket,
    *,
    battle_id: str,
    room: BattleRoom,
    db: Session,
    player_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: dict[str, Any],
    client_command_id: str,
) -> None:
    command_type = "combat.send_raid_lead_command"
    if str(player_id) != room.raid_lead_player_id:
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="NOT_RAID_LEAD",
            reason="Only raid lead can send raid lead commands.",
            retryable=False,
        )
        return

    rl_cmd = str(payload.get("command_id", "")).strip()
    if rl_cmd not in RAID_LEAD_COMMAND_IDS:
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="INVALID_PAYLOAD",
            reason="Unknown raid lead command_id.",
            retryable=False,
        )
        return

    target_payload = _normalized_target(payload)
    target_out: dict[str, Any] | None
    if rl_cmd in TARGETED_RAID_LEAD_COMMAND_IDS:
        if str(target_payload.get("kind", "")).strip() != "entity":
            await _send_command_error(
                websocket,
                battle_id=battle_id,
                room=room,
                client_command_id=client_command_id,
                command_type=command_type,
                code="INVALID_PAYLOAD",
                reason="Targeted raid lead command requires target.kind=entity.",
                retryable=False,
            )
            return
        tid = str(target_payload.get("entity_id", "")).strip()
        if tid not in room.entities or room.entity_teams.get(tid) != "enemy":
            await _send_command_error(
                websocket,
                battle_id=battle_id,
                room=room,
                client_command_id=client_command_id,
                command_type=command_type,
                code="INVALID_TARGET",
                reason="Raid lead command target must be an enemy entity.",
                retryable=False,
            )
            return
        target_out = {"kind": "entity", "entity_id": tid}
    else:
        target_out = None

    payload_hash = dedup_service.canonical_payload_hash(payload)
    try:
        dedup_result = dedup_service.reserve_command_dedup_slot(
            db,
            player_id=player_id,
            room_kind=ROOM_KIND,
            room_id=battle_id,
            client_command_id=client_command_id,
            command_type=command_type,
            payload_hash=payload_hash,
        )
    except ApiError:
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="IDEMPOTENCY_CONFLICT",
            reason="client_command_id was reused with another payload.",
            retryable=False,
        )
        return

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
                client_command_id=client_command_id,
                status_value=status_value,
                command_type=command_type,
                applied_server_seq=dedup_result.row.original_server_seq,
                original_server_seq=dedup_result.row.original_server_seq,
            ),
        )
        return

    event_seq = room.state.issue_server_seq()
    room.last_raid_lead_command = {
        "command_id": rl_cmd,
        "player_id": str(player_id),
        "target": target_out,
        "sent_at": _iso_now(),
    }
    event_payload: dict[str, Any] = {
        "event_type": "raid_lead_command_sent",
        "player_id": str(player_id),
        "command_id": rl_cmd,
        "target": target_out,
    }
    dedup_service.finalize_command_dedup_accepted(
        db, dedup_result.row, original_server_seq=event_seq
    )
    game_audit.record_game_audit_event(
        db,
        event_name="battle.raid_lead_command_sent",
        player_id=player_id,
        session_id=session_id,
        payload={
            "battle_id": battle_id,
            "command_type": command_type,
            "client_command_id": client_command_id,
            "event_payload": event_payload,
        },
    )
    db.commit()
    await _broadcast_room_message(
        battle_id,
        {
            "protocol": PROTOCOL,
            "kind": "event",
            "type": "battle.event",
            "room": {"kind": ROOM_KIND, "id": battle_id},
            "server_seq": event_seq,
            "sent_at": _iso_now(),
            "payload": event_payload,
        },
    )
    result_seq = room.state.issue_server_seq()
    await websocket.send_json(
        _result_message(
            room_id=battle_id,
            server_seq=result_seq,
            client_command_id=client_command_id,
            status_value="accepted",
            command_type=command_type,
            applied_server_seq=event_seq,
            original_server_seq=event_seq,
        ),
    )


async def _handle_send_emoji(
    websocket: WebSocket,
    *,
    battle_id: str,
    room: BattleRoom,
    db: Session,
    player_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: dict[str, Any],
    client_command_id: str,
) -> None:
    command_type = "combat.send_emoji"
    emoji_id = str(payload.get("emoji_id", "")).strip()
    if emoji_id not in EMOJI_IDS:
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="INVALID_PAYLOAD",
            reason="Unknown emoji_id.",
            retryable=False,
        )
        return

    if await STORE.is_comm_rate_limited(
        battle_id,
        str(player_id),
        "emoji",
        COMM_PULSE_MIN_INTERVAL_S,
    ):
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="RATE_LIMITED",
            reason="Emoji commands are rate limited.",
            retryable=True,
        )
        return

    payload_hash = dedup_service.canonical_payload_hash(payload)
    try:
        dedup_result = dedup_service.reserve_command_dedup_slot(
            db,
            player_id=player_id,
            room_kind=ROOM_KIND,
            room_id=battle_id,
            client_command_id=client_command_id,
            command_type=command_type,
            payload_hash=payload_hash,
        )
    except ApiError:
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="IDEMPOTENCY_CONFLICT",
            reason="client_command_id was reused with another payload.",
            retryable=False,
        )
        return

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
                client_command_id=client_command_id,
                status_value=status_value,
                command_type=command_type,
                applied_server_seq=dedup_result.row.original_server_seq,
                original_server_seq=dedup_result.row.original_server_seq,
            ),
        )
        return

    event_seq = room.state.issue_server_seq()
    event_payload = {
        "event_type": "emoji_sent",
        "player_id": str(player_id),
        "emoji_id": emoji_id,
    }
    dedup_service.finalize_command_dedup_accepted(
        db, dedup_result.row, original_server_seq=event_seq
    )
    game_audit.record_game_audit_event(
        db,
        event_name="battle.emoji_sent",
        player_id=player_id,
        session_id=session_id,
        payload={
            "battle_id": battle_id,
            "command_type": command_type,
            "client_command_id": client_command_id,
            "event_payload": event_payload,
        },
    )
    db.commit()
    await _broadcast_room_message(
        battle_id,
        {
            "protocol": PROTOCOL,
            "kind": "event",
            "type": "battle.event",
            "room": {"kind": ROOM_KIND, "id": battle_id},
            "server_seq": event_seq,
            "sent_at": _iso_now(),
            "payload": event_payload,
        },
    )
    result_seq = room.state.issue_server_seq()
    await websocket.send_json(
        _result_message(
            room_id=battle_id,
            server_seq=result_seq,
            client_command_id=client_command_id,
            status_value="accepted",
            command_type=command_type,
            applied_server_seq=event_seq,
            original_server_seq=event_seq,
        ),
    )


async def _handle_send_quick_phrase(
    websocket: WebSocket,
    *,
    battle_id: str,
    room: BattleRoom,
    db: Session,
    player_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: dict[str, Any],
    client_command_id: str,
) -> None:
    command_type = "combat.send_quick_phrase"
    phrase_id = str(payload.get("phrase_id", "")).strip()
    if phrase_id not in QUICK_PHRASE_IDS:
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="INVALID_PAYLOAD",
            reason="Unknown phrase_id.",
            retryable=False,
        )
        return

    if await STORE.is_comm_rate_limited(
        battle_id,
        str(player_id),
        "phrase",
        COMM_PULSE_MIN_INTERVAL_S,
    ):
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="RATE_LIMITED",
            reason="Quick phrases are rate limited.",
            retryable=True,
        )
        return

    payload_hash = dedup_service.canonical_payload_hash(payload)
    try:
        dedup_result = dedup_service.reserve_command_dedup_slot(
            db,
            player_id=player_id,
            room_kind=ROOM_KIND,
            room_id=battle_id,
            client_command_id=client_command_id,
            command_type=command_type,
            payload_hash=payload_hash,
        )
    except ApiError:
        await _send_command_error(
            websocket,
            battle_id=battle_id,
            room=room,
            client_command_id=client_command_id,
            command_type=command_type,
            code="IDEMPOTENCY_CONFLICT",
            reason="client_command_id was reused with another payload.",
            retryable=False,
        )
        return

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
                client_command_id=client_command_id,
                status_value=status_value,
                command_type=command_type,
                applied_server_seq=dedup_result.row.original_server_seq,
                original_server_seq=dedup_result.row.original_server_seq,
            ),
        )
        return

    event_seq = room.state.issue_server_seq()
    event_payload = {
        "event_type": "quick_phrase_sent",
        "player_id": str(player_id),
        "phrase_id": phrase_id,
    }
    dedup_service.finalize_command_dedup_accepted(
        db, dedup_result.row, original_server_seq=event_seq
    )
    game_audit.record_game_audit_event(
        db,
        event_name="battle.quick_phrase_sent",
        player_id=player_id,
        session_id=session_id,
        payload={
            "battle_id": battle_id,
            "command_type": command_type,
            "client_command_id": client_command_id,
            "event_payload": event_payload,
        },
    )
    db.commit()
    await _broadcast_room_message(
        battle_id,
        {
            "protocol": PROTOCOL,
            "kind": "event",
            "type": "battle.event",
            "room": {"kind": ROOM_KIND, "id": battle_id},
            "server_seq": event_seq,
            "sent_at": _iso_now(),
            "payload": event_payload,
        },
    )
    result_seq = room.state.issue_server_seq()
    await websocket.send_json(
        _result_message(
            room_id=battle_id,
            server_seq=result_seq,
            client_command_id=client_command_id,
            status_value="accepted",
            command_type=command_type,
            applied_server_seq=event_seq,
            original_server_seq=event_seq,
        ),
    )


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
    await STORE.add_connection(battle_id, websocket)
    raid_lead_player_id = str(
        next((m.player_id for m in members if m.is_raid_lead), members[0].player_id),
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
            await STORE.remove_connection(battle_id, websocket)
            break

        kind = message.get("kind")
        msg_type = str(message.get("type", "")).strip()
        command_id = str(message.get("client_command_id", "")).strip()
        payload = message.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        msg_room = message.get("room") or {}

        envelope_ok = (
            kind == "command"
            and msg_room.get("kind") == ROOM_KIND
            and str(msg_room.get("id")) == battle_id
            and bool(command_id)
        )
        if not envelope_ok:
            seq = room.state.issue_server_seq()
            await websocket.send_json(
                _error_message(
                    room_id=battle_id,
                    server_seq=seq,
                    client_command_id=command_id or "missing_command_id",
                    command_type=msg_type or "unknown",
                    code="INVALID_PAYLOAD",
                    reason="Invalid command envelope.",
                    retryable=False,
                ),
            )
            continue

        if msg_type == "combat.use_skill":
            requested_actor_id = str(payload.get("actor_entity_id", "")).strip()
            if requested_actor_id != actor_entity_id:
                await _send_command_error(
                    websocket,
                    battle_id=battle_id,
                    room=room,
                    client_command_id=command_id,
                    command_type=msg_type,
                    code="UNAUTHORIZED",
                    reason="Actor does not belong to current session.",
                    retryable=False,
                )
                continue
            await _handle_use_skill(
                websocket,
                battle_id=battle_id,
                room=room,
                db=db,
                player_id=player_id,
                session_id=session_id,
                actor_entity_id=actor_entity_id,
                payload=payload,
                client_command_id=command_id,
            )
        elif msg_type == "combat.send_raid_lead_command":
            await _handle_send_raid_lead_command(
                websocket,
                battle_id=battle_id,
                room=room,
                db=db,
                player_id=player_id,
                session_id=session_id,
                payload=payload,
                client_command_id=command_id,
            )
        elif msg_type == "combat.send_emoji":
            await _handle_send_emoji(
                websocket,
                battle_id=battle_id,
                room=room,
                db=db,
                player_id=player_id,
                session_id=session_id,
                payload=payload,
                client_command_id=command_id,
            )
        elif msg_type == "combat.send_quick_phrase":
            await _handle_send_quick_phrase(
                websocket,
                battle_id=battle_id,
                room=room,
                db=db,
                player_id=player_id,
                session_id=session_id,
                payload=payload,
                client_command_id=command_id,
            )
        else:
            await _send_command_error(
                websocket,
                battle_id=battle_id,
                room=room,
                client_command_id=command_id,
                command_type=msg_type,
                code="UNSUPPORTED_PROTOCOL",
                reason="Unsupported command type.",
                retryable=False,
            )
