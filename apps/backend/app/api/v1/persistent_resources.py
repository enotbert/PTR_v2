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
    AddTavernContributionBody,
    AnalyticsDebugEventListOut,
    InviteDetailOut,
    PartyCreateBody,
    PartyDetailOut,
    PartyJoinBody,
    PartyLoadoutPatchBody,
    PlayerTavernStateOut,
    RaidCreateBody,
    RaidDetailOut,
    RewardListOut,
)
from app.schemas.session import ErrorBody
from app.services.raid_setup import (
    create_party as create_party_service,
)
from app.services.raid_setup import (
    create_raid as create_raid_service,
)
from app.services.raid_setup import (
    get_party as get_party_service,
)
from app.services.raid_setup import (
    get_raid as get_raid_service,
)
from app.services.raid_setup import (
    join_party as join_party_service,
)
from app.services.raid_setup import (
    update_my_loadout as update_my_loadout_service,
)
from app.services.tavern import add_tavern_contribution, read_tavern_state

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
    """Read tavern home state bundle (project, summary, and short chronicle)."""

    return read_tavern_state(db, player_id=player_id, tavern_id=tavern_id)


@router.post(
    "/taverns/{tavern_id}/contributions",
    response_model=PlayerTavernStateOut,
    tags=["Tavern v1"],
    operation_id="v1_add_tavern_contribution",
    responses={400: {"model": ErrorBody}, 401: {"model": ErrorBody}, 404: {"model": ErrorBody}},
)
def post_tavern_contribution(
    tavern_id: uuid.UUID,
    body: AddTavernContributionBody,
    db: Annotated[Session, Depends(get_db)],
    player_id: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> PlayerTavernStateOut:
    """Server-authoritative contribution write; client only sends intent."""

    return add_tavern_contribution(
        db,
        player_id=player_id,
        tavern_id=tavern_id,
        amount=body.amount,
        source_type=body.source_type,
        source_ref=body.source_ref,
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
    """Read party details for current member."""

    return get_party_service(db, party_id=party_id, player_id=player_id)


@router.post(
    "/parties",
    response_model=PartyDetailOut,
    tags=["Party v1"],
    operation_id="v1_create_party",
    responses={400: {"model": ErrorBody}, 401: {"model": ErrorBody}},
)
def create_party(
    body: PartyCreateBody,
    db: Annotated[Session, Depends(get_db)],
    player_id: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> PartyDetailOut:
    return create_party_service(
        db,
        player_id=player_id,
        tavern_id=body.tavern_id,
        role_id=body.role_id,
        loadout_skill_ids=body.loadout_skill_ids,
    )


@router.post(
    "/parties/{party_id}/join",
    response_model=PartyDetailOut,
    tags=["Party v1"],
    operation_id="v1_join_party",
    responses={400: {"model": ErrorBody}, 401: {"model": ErrorBody}, 404: {"model": ErrorBody}},
)
def join_party(
    party_id: uuid.UUID,
    body: PartyJoinBody,
    db: Annotated[Session, Depends(get_db)],
    player_id: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> PartyDetailOut:
    return join_party_service(
        db,
        party_id=party_id,
        player_id=player_id,
        role_id=body.role_id,
        loadout_skill_ids=body.loadout_skill_ids,
    )


@router.patch(
    "/parties/{party_id}/members/me/loadout",
    response_model=PartyDetailOut,
    tags=["Party v1"],
    operation_id="v1_update_my_party_loadout",
    responses={400: {"model": ErrorBody}, 401: {"model": ErrorBody}, 404: {"model": ErrorBody}},
)
def update_my_party_loadout(
    party_id: uuid.UUID,
    body: PartyLoadoutPatchBody,
    db: Annotated[Session, Depends(get_db)],
    player_id: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> PartyDetailOut:
    return update_my_loadout_service(
        db,
        party_id=party_id,
        player_id=player_id,
        role_id=body.role_id,
        loadout_skill_ids=body.loadout_skill_ids,
    )


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
    player_id: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> RaidDetailOut:
    """Read raid metadata for party member."""

    return get_raid_service(db, raid_id=raid_id, player_id=player_id)


@router.post(
    "/raids",
    response_model=RaidDetailOut,
    tags=["Raid v1"],
    operation_id="v1_create_raid",
    responses={400: {"model": ErrorBody}, 401: {"model": ErrorBody}, 404: {"model": ErrorBody}},
)
def create_raid(
    body: RaidCreateBody,
    db: Annotated[Session, Depends(get_db)],
    player_id: Annotated[uuid.UUID, Depends(require_session_player_id)],
) -> RaidDetailOut:
    return create_raid_service(
        db,
        player_id=player_id,
        party_id=body.party_id,
        tavern_id=body.tavern_id,
        raid_template_id=body.raid_template_id,
    )


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
        "PTR-72",
        "Reward claim API is not implemented yet (see Linear PTR-72).",
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
