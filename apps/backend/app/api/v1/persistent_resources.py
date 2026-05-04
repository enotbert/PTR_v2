"""V1 REST skeleton: tavern, party/raid, rewards, invites, analytics.

Placeholder handlers return deterministic minimal payloads or ``501`` with
``ApiError`` (see ``docs/tech/rest-v1-skeleton.md`` for Linear follow-ups).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_session_player_id
from app.db import get_db
from app.errors import ApiError
from app.schemas.resources_v1 import (
    AnalyticsDebugEventListOut,
    InviteDetailOut,
    PartyDetailOut,
    PlayerTavernStateOut,
    RaidDetailOut,
    RewardListOut,
)
from app.schemas.session import ErrorBody

router = APIRouter()


def _now() -> datetime:
    return datetime.now(UTC)


def _not_implemented(tracked_by: str, summary: str) -> None:
    raise ApiError(
        status_code=501,
        error="not_implemented",
        message=summary,
        details={"tracked_by": tracked_by},
    )


@router.get(
    "/taverns/{tavern_id}/state",
    response_model=PlayerTavernStateOut,
    tags=["Tavern v1"],
    operation_id="v1_get_tavern_player_state",
    responses={401: {"model": ErrorBody}, 404: {"model": ErrorBody}},
)
def get_tavern_player_state(
    tavern_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    player_id: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> PlayerTavernStateOut:
    """Placeholder tavern progression read (implementation: PTR-35)."""

    _ = db  # reserved for DB-backed read
    return PlayerTavernStateOut(
        tavern_id=tavern_id,
        player_id=player_id,
        reputation=0,
        weekly_points=0,
        updated_at=_now(),
    )


@router.get(
    "/parties/{party_id}",
    response_model=PartyDetailOut,
    tags=["Party v1"],
    operation_id="v1_get_party",
    responses={401: {"model": ErrorBody}, 404: {"model": ErrorBody}},
)
def get_party(
    party_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    player_id: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> PartyDetailOut:
    """Placeholder party read (implementation: PTR-37)."""

    _ = db
    return PartyDetailOut(
        id=party_id,
        tavern_id=uuid.UUID(int=0),
        created_by_player_id=player_id,
        status="open",
        members=[],
    )


@router.post(
    "/parties",
    response_model=None,
    tags=["Party v1"],
    operation_id="v1_create_party",
    responses={401: {"model": ErrorBody}, 501: {"model": ErrorBody}},
)
def create_party(_: Annotated[uuid.UUID, Depends(require_session_player_id)]) -> NoReturn:
    _not_implemented("PTR-37", "Party creation is not implemented yet.")


@router.get(
    "/raids/{raid_id}",
    response_model=RaidDetailOut,
    tags=["Raid v1"],
    operation_id="v1_get_raid",
    responses={401: {"model": ErrorBody}, 404: {"model": ErrorBody}},
)
def get_raid(
    raid_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> RaidDetailOut:
    """Placeholder raid read (implementation: PTR-37)."""

    _ = db
    return RaidDetailOut(
        id=raid_id,
        party_id=uuid.UUID(int=0),
        raid_template_id="unknown",
        status="pending",
    )


@router.post(
    "/raids",
    response_model=None,
    tags=["Raid v1"],
    operation_id="v1_create_raid",
    responses={401: {"model": ErrorBody}, 501: {"model": ErrorBody}},
)
def create_raid(_: Annotated[uuid.UUID, Depends(require_session_player_id)]) -> NoReturn:
    _not_implemented("PTR-37", "Raid creation is not implemented yet.")


@router.get(
    "/players/me/rewards",
    response_model=RewardListOut,
    tags=["Rewards v1"],
    operation_id="v1_list_my_rewards",
    responses={401: {"model": ErrorBody}},
)
def list_my_rewards(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> RewardListOut:
    """Placeholder rewards list (persistence and claim flow follow separate issues)."""

    _ = db
    return RewardListOut(items=[])


@router.post(
    "/rewards/{reward_id}/claims",
    response_model=None,
    tags=["Rewards v1"],
    operation_id="v1_claim_reward",
    responses={401: {"model": ErrorBody}, 501: {"model": ErrorBody}},
)
def claim_reward(
    reward_id: uuid.UUID,
    _session_player_id: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> NoReturn:
    _ = (reward_id, _session_player_id)
    _not_implemented(
        "PTR-32-follow-up",
        "Reward claim API is not scheduled yet; open a follow-up from PTR-32.",
    )


@router.post(
    "/invites",
    response_model=None,
    tags=["Invites v1"],
    operation_id="v1_create_invite",
    responses={401: {"model": ErrorBody}, 501: {"model": ErrorBody}},
)
def create_invite(_: Annotated[uuid.UUID, Depends(require_session_player_id)]) -> NoReturn:
    _not_implemented("PTR-55", "Invite creation is not implemented yet.")


@router.get(
    "/invites/by-token/{token}",
    response_model=InviteDetailOut,
    tags=["Invites v1"],
    operation_id="v1_get_invite_by_token",
    responses={404: {"model": ErrorBody}},
)
def get_invite_by_token(token: str) -> InviteDetailOut:
    """Public-shape preview for resolver UIs (implementation: PTR-55)."""

    now = _now()
    return InviteDetailOut(
        id=uuid.UUID(int=0),
        created_by_player_id=uuid.UUID(int=0),
        raid_id=None,
        token=token,
        status="active",
        created_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=7),
        used_at=None,
    )


@router.get(
    "/analytics/debug/recent-events",
    response_model=AnalyticsDebugEventListOut,
    tags=["Analytics v1"],
    operation_id="v1_list_analytics_debug_events",
    responses={401: {"model": ErrorBody}},
)
def list_analytics_debug_events(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[uuid.UUID, Depends(require_session_player_id)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AnalyticsDebugEventListOut:
    """Debug-only read of recent analytics rows (implementation TBD; gated auth later)."""

    _ = db
    _ = limit
    return AnalyticsDebugEventListOut(items=[])
