"""Server-authoritative raid outcome and reward issuing."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.party_raid import Party, PartyMember, Raid
from app.models.tavern import TavernContribution
from app.services import game_audit
from app.services.tavern import add_tavern_contribution

COMPLETED_REWARD_POINTS = 30
FAILED_APPROVED_REWARD_POINTS = 10


@dataclass(frozen=True)
class RaidResolution:
    raid_id: uuid.UUID
    status: str
    reward_issued_points: int
    reward_record_ids: list[str]
    claim_status: str
    newly_issued_reward_record_ids: list[str]
    existing_reward_record_ids: list[str]
    approved_failed_progress: bool


def _now() -> datetime:
    return datetime.now(UTC)


def _get_active_raid(db: Session, party_id: uuid.UUID) -> Raid | None:
    stmt: Select[tuple[Raid]] = (
        select(Raid)
        .where(Raid.party_id == party_id, Raid.status.in_(("pending", "active")))
        .order_by(Raid.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _latest_raid(db: Session, party_id: uuid.UUID) -> Raid | None:
    stmt: Select[tuple[Raid]] = (
        select(Raid).where(Raid.party_id == party_id).order_by(Raid.id.desc()).limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _get_or_create_active_raid(db: Session, party_id: uuid.UUID) -> Raid:
    raid = _get_active_raid(db, party_id)
    if raid is not None:
        return raid
    raid = Raid(
        party_id=party_id,
        raid_template_id="regular_party_v1",
        status="active",
        started_at=_now(),
        ended_at=None,
    )
    db.add(raid)
    db.flush()
    return raid


def mark_raid_active_for_party(db: Session, party_id: uuid.UUID) -> Raid | None:
    party = db.get(Party, party_id)
    if party is None:
        return None
    raid = _get_or_create_active_raid(db, party_id)
    if raid.status == "pending":
        raid.status = "active"
        raid.started_at = raid.started_at or _now()
        db.add(raid)
        db.flush()
    return raid


def _raid_members(db: Session, party_id: uuid.UUID) -> list[PartyMember]:
    stmt: Select[tuple[PartyMember]] = select(PartyMember).where(
        PartyMember.party_id == party_id,
        PartyMember.left_at.is_(None),
    )
    return list(db.execute(stmt).scalars().all())


def _is_active_party_member(db: Session, *, party_id: uuid.UUID, player_id: uuid.UUID) -> bool:
    stmt: Select[tuple[PartyMember]] = (
        select(PartyMember)
        .where(
            PartyMember.party_id == party_id,
            PartyMember.player_id == player_id,
            PartyMember.left_at.is_(None),
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def _existing_reward(
    db: Session, *, player_id: uuid.UUID, tavern_id: uuid.UUID, raid_id: uuid.UUID
) -> TavernContribution | None:
    stmt: Select[tuple[TavernContribution]] = (
        select(TavernContribution)
        .where(
            TavernContribution.player_id == player_id,
            TavernContribution.tavern_id == tavern_id,
            TavernContribution.source_type == "raid_reward",
            TavernContribution.source_ref == f"raid:{raid_id}",
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def resolve_raid_outcome_and_issue_rewards(
    db: Session,
    *,
    party_id: uuid.UUID,
    enemies_defeated: bool,
    allies_defeated: bool,
    approved_failed_progress: bool,
    triggered_by_player_id: uuid.UUID,
    session_id: uuid.UUID,
) -> RaidResolution:
    party = db.get(Party, party_id)
    if party is None:
        raise ValueError("PARTY_NOT_FOUND")
    if not _is_active_party_member(db, party_id=party_id, player_id=triggered_by_player_id):
        raise ValueError("PLAYER_NOT_IN_PARTY")
    active_raid = _get_active_raid(db, party_id)
    if active_raid is not None:
        raid = active_raid
        already_finalized = False
    else:
        latest_raid = _latest_raid(db, party_id)
        if latest_raid is not None and latest_raid.status in ("completed", "failed"):
            raid = latest_raid
            already_finalized = True
        else:
            raid = _get_or_create_active_raid(db, party_id)
            already_finalized = False

    if already_finalized:
        status = raid.status
        if status == "completed":
            reward_points = COMPLETED_REWARD_POINTS
        else:
            existing_failed_reward = False
            for member in _raid_members(db, party_id):
                if (
                    _existing_reward(
                        db, player_id=member.player_id, tavern_id=party.tavern_id, raid_id=raid.id
                    )
                    is not None
                ):
                    existing_failed_reward = True
                    break
            reward_points = FAILED_APPROVED_REWARD_POINTS if existing_failed_reward else 0
    elif enemies_defeated:
        status = "completed"
        reward_points = COMPLETED_REWARD_POINTS
    elif allies_defeated or approved_failed_progress:
        status = "failed"
        reward_points = FAILED_APPROVED_REWARD_POINTS if approved_failed_progress else 0
    else:
        raise ValueError("OUTCOME_NOT_FINAL")

    if not already_finalized:
        raid.status = status
        raid.started_at = raid.started_at or _now()
        raid.ended_at = _now()
        db.add(raid)

    reward_record_ids: list[str] = []
    newly_issued_reward_record_ids: list[str] = []
    existing_reward_record_ids: list[str] = []
    if reward_points > 0:
        for member in _raid_members(db, party_id):
            existing = _existing_reward(
                db, player_id=member.player_id, tavern_id=party.tavern_id, raid_id=raid.id
            )
            if existing is not None:
                existing_id = str(existing.id)
                reward_record_ids.append(existing_id)
                existing_reward_record_ids.append(existing_id)
                continue
            state = add_tavern_contribution(
                db,
                player_id=member.player_id,
                tavern_id=party.tavern_id,
                amount=reward_points,
                source_type="raid_reward",
                source_ref=f"raid:{raid.id}",
            )
            latest_id = state.chronicle[0].id if state.chronicle else None
            if latest_id is not None:
                latest_id_str = str(latest_id)
                reward_record_ids.append(latest_id_str)
                newly_issued_reward_record_ids.append(latest_id_str)

    claim_status = "not_applicable"
    if reward_points > 0:
        claim_status = "claimed" if newly_issued_reward_record_ids else "already_claimed"

    game_audit.record_game_audit_event(
        db,
        event_name="raid.outcome_resolved",
        player_id=triggered_by_player_id,
        session_id=session_id,
        payload={
            "raid_id": str(raid.id),
            "party_id": str(party_id),
            "status": status,
            "approved_failed_progress": approved_failed_progress,
            "reward_points_per_member": reward_points,
            "claim_status": claim_status,
            "idempotency_key": f"raid:{raid.id}",
            "reward_record_ids": reward_record_ids,
            "newly_issued_reward_record_ids": newly_issued_reward_record_ids,
            "existing_reward_record_ids": existing_reward_record_ids,
        },
    )
    db.flush()
    return RaidResolution(
        raid_id=raid.id,
        status=status,
        reward_issued_points=reward_points,
        reward_record_ids=reward_record_ids,
        claim_status=claim_status,
        newly_issued_reward_record_ids=newly_issued_reward_record_ids,
        existing_reward_record_ids=existing_reward_record_ids,
        approved_failed_progress=approved_failed_progress,
    )
