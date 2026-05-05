"""Tavern state read/update service (server-authoritative progression)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models.tavern import PlayerTavernState, Tavern, TavernContribution
from app.schemas.resources_v1 import (
    PlayerTavernStateOut,
    TavernChronicleEntryOut,
    TavernContributionSummaryOut,
    TavernProjectOut,
    TavernRefOut,
)

MAX_CONTRIBUTION_AMOUNT = 10_000
RECENT_CHRONICLE_LIMIT = 5
PROJECT_TARGET_POINTS = 1_000


def _now() -> datetime:
    return datetime.now(UTC)


def _default_tavern_copy(tavern_id: uuid.UUID) -> tuple[str, str]:
    short = str(tavern_id).split("-", maxsplit=1)[0]
    return f"tavern-{short}", "Starter Tavern"


def ensure_tavern(db: Session, tavern_id: uuid.UUID) -> Tavern:
    tavern = db.get(Tavern, tavern_id)
    if tavern is not None:
        return tavern
    now = _now()
    slug, name = _default_tavern_copy(tavern_id)
    tavern = Tavern(
        id=tavern_id,
        slug=slug,
        name=name,
        tier=0,
        created_at=now,
        updated_at=now,
    )
    db.add(tavern)
    db.flush()
    return tavern


def ensure_player_tavern_state(
    db: Session,
    player_id: uuid.UUID,
    tavern_id: uuid.UUID,
) -> PlayerTavernState:
    row = db.scalar(
        select(PlayerTavernState).where(
            PlayerTavernState.player_id == player_id,
            PlayerTavernState.tavern_id == tavern_id,
        )
    )
    if row is not None:
        return row
    row = PlayerTavernState(
        player_id=player_id,
        tavern_id=tavern_id,
        reputation=0,
        weekly_points=0,
        updated_at=_now(),
    )
    db.add(row)
    db.flush()
    return row


def _recent_chronicle_entries(
    db: Session, player_id: uuid.UUID, tavern_id: uuid.UUID
) -> list[TavernChronicleEntryOut]:
    rows = db.scalars(
        select(TavernContribution)
        .where(
            TavernContribution.player_id == player_id,
            TavernContribution.tavern_id == tavern_id,
        )
        .order_by(TavernContribution.created_at.desc())
        .limit(RECENT_CHRONICLE_LIMIT)
    ).all()
    return [
        TavernChronicleEntryOut(
            id=r.id,
            source_type=r.source_type,
            source_ref=r.source_ref,
            amount=r.amount,
            created_at=r.created_at,
        )
        for r in rows
    ]


def read_tavern_state(
    db: Session,
    player_id: uuid.UUID,
    tavern_id: uuid.UUID,
) -> PlayerTavernStateOut:
    tavern = ensure_tavern(db, tavern_id)
    state = ensure_player_tavern_state(db, player_id, tavern_id)
    chronicle = _recent_chronicle_entries(db, player_id, tavern_id)
    summary = TavernContributionSummaryOut(
        total_points=state.weekly_points,
        latest_amount=chronicle[0].amount if chronicle else None,
        latest_source_type=chronicle[0].source_type if chronicle else None,
        latest_at=chronicle[0].created_at if chronicle else None,
    )
    project = TavernProjectOut(
        id="weekly_route_reopening",
        title="Reopen the blocked route",
        status="active",
        progress_points=state.weekly_points,
        target_points=PROJECT_TARGET_POINTS,
    )
    return PlayerTavernStateOut(
        tavern=TavernRefOut(id=tavern.id, slug=tavern.slug, name=tavern.name, tier=tavern.tier),
        tavern_id=tavern.id,
        player_id=player_id,
        reputation=state.reputation,
        weekly_points=state.weekly_points,
        updated_at=state.updated_at,
        current_project=project,
        contribution_summary=summary,
        chronicle=chronicle,
    )


def add_tavern_contribution(
    db: Session,
    *,
    player_id: uuid.UUID,
    tavern_id: uuid.UUID,
    amount: int,
    source_type: str,
    source_ref: str | None,
) -> PlayerTavernStateOut:
    if amount <= 0:
        raise ApiError(
            status_code=400,
            error="invalid_contribution_amount",
            message="Contribution amount must be greater than zero.",
        )
    if amount > MAX_CONTRIBUTION_AMOUNT:
        raise ApiError(
            status_code=400,
            error="contribution_amount_too_large",
            message=f"Contribution amount must be <= {MAX_CONTRIBUTION_AMOUNT}.",
            details={"max_amount": MAX_CONTRIBUTION_AMOUNT},
        )

    ensure_tavern(db, tavern_id)
    state = ensure_player_tavern_state(db, player_id, tavern_id)
    now = _now()
    db.add(
        TavernContribution(
            player_id=player_id,
            tavern_id=tavern_id,
            source_type=source_type,
            source_ref=source_ref,
            amount=amount,
            created_at=now,
        )
    )
    state.weekly_points += amount
    state.reputation += amount
    state.updated_at = now
    db.add(state)
    db.flush()
    return read_tavern_state(db, player_id=player_id, tavern_id=tavern_id)
