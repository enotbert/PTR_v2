"""WebSocket lobby room endpoint (PTR-38)."""

from __future__ import annotations

import asyncio
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
from app.models.party_raid import Party, PartyMember, Raid
from app.services import command_dedup as dedup_service
from app.services.session import assert_active_session_player_id

router = APIRouter()

PROTOCOL = "ptr.ws.v1"
ROOM_KIND = "lobby"
ALLOWED_PLAYER_STATUS = {"not_ready", "ready", "away"}


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass
class LobbyRoomState:
    next_server_seq: int = 1
    player_status: dict[str, str] = field(default_factory=dict)

    def issue_server_seq(self) -> int:
        value = self.next_server_seq
        self.next_server_seq += 1
        return value


class LobbyWsStore:
    def __init__(self) -> None:
        self._rooms: dict[str, LobbyRoomState] = {}
        self._lock = asyncio.Lock()

    async def get_room(self, lobby_id: str) -> LobbyRoomState:
        async with self._lock:
            room = self._rooms.get(lobby_id)
            if room is None:
                room = LobbyRoomState()
                self._rooms[lobby_id] = room
            return room

    async def set_player_status(self, lobby_id: str, player_id: str, value: str) -> None:
        room = await self.get_room(lobby_id)
        async with self._lock:
            room.player_status[player_id] = value

    async def get_player_status(self, lobby_id: str, player_id: str) -> str:
        room = await self.get_room(lobby_id)
        async with self._lock:
            return room.player_status.get(player_id, "not_ready")

    async def issue_server_seq(self, lobby_id: str) -> int:
        room = await self.get_room(lobby_id)
        async with self._lock:
            return room.issue_server_seq()


STORE = LobbyWsStore()


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


def _load_party_membership(
    db: Session, lobby_id: uuid.UUID, player_id: uuid.UUID
) -> list[PartyMember]:
    party = db.get(Party, lobby_id)
    if party is None:
        raise ApiError(status_code=404, error="room_not_found", message="Lobby was not found.")
    stmt: Select[tuple[PartyMember]] = select(PartyMember).where(
        PartyMember.party_id == lobby_id,
        PartyMember.left_at.is_(None),
    )
    members = list(db.execute(stmt).scalars().all())
    if not any(member.player_id == player_id for member in members):
        raise ApiError(
            status_code=403,
            error="room_forbidden",
            message="Player is not in this lobby.",
        )
    return members


def _load_latest_raid_id(db: Session, party_id: uuid.UUID) -> str:
    stmt: Select[tuple[Raid]] = (
        select(Raid).where(Raid.party_id == party_id).order_by(Raid.id.desc()).limit(1)
    )
    latest = db.execute(stmt).scalar_one_or_none()
    if latest is None:
        return f"raid_{party_id}"
    return str(latest.id)


async def _build_snapshot_payload(
    db: Session, *, lobby_id: uuid.UUID, members: list[PartyMember]
) -> dict[str, Any]:
    players: list[dict[str, Any]] = []
    for member in members:
        pid = str(member.player_id)
        players.append(
            {
                "player_id": pid,
                "role_id": member.role_id,
                "status": await STORE.get_player_status(str(lobby_id), pid),
                "is_raid_lead": member.is_raid_lead,
            }
        )
    return {
        "lobby_id": str(lobby_id),
        "raid_id": _load_latest_raid_id(db, lobby_id),
        "phase": "waiting",
        "players": players,
        "party_recommendations": [],
        "weekly_event": None,
    }


def _result_message(
    *,
    lobby_id: str,
    server_seq: int,
    client_command_id: str,
    command_type: str,
    status_value: str,
    applied_server_seq: int | None,
    original_server_seq: int | None,
) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "kind": "result",
        "type": "command.result",
        "room": {"kind": ROOM_KIND, "id": lobby_id},
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
    lobby_id: str,
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
        "room": {"kind": ROOM_KIND, "id": lobby_id},
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


@router.websocket("/ws/lobbies/{lobby_id}")
async def lobby_room_ws(
    websocket: WebSocket,
    lobby_id: str,
    db: Session = Depends(get_db),  # noqa: B008 - FastAPI dependency injection pattern
) -> None:
    await websocket.accept()
    try:
        lobby_uuid = uuid.UUID(lobby_id)
        session_id = _parse_ws_session_id(websocket)
        player_id = assert_active_session_player_id(db, session_id)
        members = _load_party_membership(db, lobby_uuid, player_id)
    except ApiError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    snapshot_seq = await STORE.issue_server_seq(lobby_id)
    snapshot_payload = await _build_snapshot_payload(db, lobby_id=lobby_uuid, members=members)
    await websocket.send_json(
        {
            "protocol": PROTOCOL,
            "kind": "snapshot",
            "type": "lobby.snapshot",
            "room": {"kind": ROOM_KIND, "id": lobby_id},
            "server_seq": snapshot_seq,
            "sent_at": _iso_now(),
            "payload": snapshot_payload,
        }
    )

    while True:
        try:
            message = await websocket.receive_json()
        except WebSocketDisconnect:
            break

        kind = message.get("kind")
        msg_type = message.get("type")
        command_id = str(message.get("client_command_id", "")).strip()
        room = message.get("room") or {}
        payload = message.get("payload") or {}

        if (
            kind != "command"
            or msg_type != "lobby.set_player_status"
            or room.get("kind") != ROOM_KIND
            or str(room.get("id")) != lobby_id
            or not command_id
        ):
            err_seq = await STORE.issue_server_seq(lobby_id)
            await websocket.send_json(
                _error_message(
                    lobby_id=lobby_id,
                    server_seq=err_seq,
                    client_command_id=command_id or "missing_command_id",
                    command_type="lobby.set_player_status",
                    code="INVALID_PAYLOAD",
                    reason="Invalid command envelope.",
                    retryable=False,
                )
            )
            continue

        next_status = str(payload.get("status", "")).strip()
        if next_status not in ALLOWED_PLAYER_STATUS:
            err_seq = await STORE.issue_server_seq(lobby_id)
            await websocket.send_json(
                _error_message(
                    lobby_id=lobby_id,
                    server_seq=err_seq,
                    client_command_id=command_id,
                    command_type="lobby.set_player_status",
                    code="INVALID_PAYLOAD",
                    reason="Unsupported status value.",
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
                room_id=lobby_id,
                client_command_id=command_id,
                command_type="lobby.set_player_status",
                payload_hash=payload_hash,
            )
        except ApiError:
            err_seq = await STORE.issue_server_seq(lobby_id)
            await websocket.send_json(
                _error_message(
                    lobby_id=lobby_id,
                    server_seq=err_seq,
                    client_command_id=command_id,
                    command_type="lobby.set_player_status",
                    code="IDEMPOTENCY_CONFLICT",
                    reason="client_command_id was reused with another payload.",
                    retryable=False,
                )
            )
            continue

        if isinstance(dedup_result, dedup_service.CommandDedupDuplicate):
            duplicate_seq = await STORE.issue_server_seq(lobby_id)
            duplicate_kind = (
                "duplicate"
                if dedup_result.row.result_kind == dedup_service.RESULT_ACCEPTED
                else "accepted"
            )
            await websocket.send_json(
                _result_message(
                    lobby_id=lobby_id,
                    server_seq=duplicate_seq,
                    client_command_id=command_id,
                    command_type="lobby.set_player_status",
                    status_value=duplicate_kind,
                    applied_server_seq=dedup_result.row.original_server_seq,
                    original_server_seq=dedup_result.row.original_server_seq,
                )
            )
            continue

        await STORE.set_player_status(lobby_id, str(player_id), next_status)
        event_seq = await STORE.issue_server_seq(lobby_id)
        dedup_service.finalize_command_dedup_accepted(
            db, dedup_result.row, original_server_seq=event_seq
        )
        db.commit()
        await websocket.send_json(
            {
                "protocol": PROTOCOL,
                "kind": "event",
                "type": "lobby.event",
                "room": {"kind": ROOM_KIND, "id": lobby_id},
                "server_seq": event_seq,
                "sent_at": _iso_now(),
                "payload": {
                    "event_type": "player_status_changed",
                    "player_id": str(player_id),
                    "status": next_status,
                },
            }
        )
        result_seq = await STORE.issue_server_seq(lobby_id)
        await websocket.send_json(
            _result_message(
                lobby_id=lobby_id,
                server_seq=result_seq,
                client_command_id=command_id,
                command_type="lobby.set_player_status",
                status_value="accepted",
                applied_server_seq=event_seq,
                original_server_seq=event_seq,
            )
        )
