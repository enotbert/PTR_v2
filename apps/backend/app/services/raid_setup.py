"""Party/raid setup services with role+loadout validation."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models.party_raid import Party, PartyMember, Raid
from app.schemas.resources_v1 import PartyDetailOut, PartyMemberOut, RaidDetailOut

DEFAULT_ROLE_ID = "vanguard"
TUTORIAL_RAID_TEMPLATE_ID = "tutorial_solo_v1"

ROLE_SKILLS: dict[str, tuple[str, str, str]] = {
    "vanguard": ("vanguard_strike", "guard_ally", "taunt_signal"),
    "arcweaver": ("arc_bolt", "rune_overload", "phase_disrupt"),
    "machinist_priest": ("mend_protocol", "cleanse_routine", "stabilize_party"),
    "signal_bard": ("signal_shot", "mark_target", "rally_chord"),
}

RAID_TEMPLATES = {"tutorial_solo_v1", "regular_party_v1"}


def _now() -> datetime:
    return datetime.now(UTC)


def _get_active_member(
    db: Session, party_id: uuid.UUID, player_id: uuid.UUID
) -> PartyMember | None:
    stmt: Select[tuple[PartyMember]] = select(PartyMember).where(
        PartyMember.party_id == party_id,
        PartyMember.player_id == player_id,
        PartyMember.left_at.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


def _get_party_or_404(db: Session, party_id: uuid.UUID) -> Party:
    party = db.get(Party, party_id)
    if party is None:
        raise ApiError(status_code=404, error="party_not_found", message="Party was not found.")
    return party


def _serialize_skills(skills: list[str]) -> str:
    return json.dumps(skills, ensure_ascii=True, separators=(",", ":"))


def _deserialize_skills(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError(value)
    return [str(item) for item in parsed]


def _validate_loadout(role_id: str, loadout_skill_ids: list[str] | None) -> list[str]:
    if role_id not in ROLE_SKILLS:
        raise ApiError(
            status_code=400,
            error="invalid_role",
            message="Role is not supported in v1.",
            details={"allowed_role_ids": sorted(ROLE_SKILLS.keys())},
        )
    default = list(ROLE_SKILLS[role_id])
    if loadout_skill_ids is None:
        return default
    if len(loadout_skill_ids) != 3:
        raise ApiError(
            status_code=400,
            error="invalid_loadout_size",
            message="Loadout must contain exactly 3 skills.",
            details={"role_id": role_id},
        )
    if len(set(loadout_skill_ids)) != 3:
        raise ApiError(
            status_code=400,
            error="duplicate_loadout_skill",
            message="Loadout cannot contain duplicate skill ids.",
            details={"role_id": role_id},
        )
    allowed = set(ROLE_SKILLS[role_id])
    unknown = [skill for skill in loadout_skill_ids if skill not in allowed]
    if unknown:
        raise ApiError(
            status_code=400,
            error="invalid_loadout_skill",
            message="Loadout contains skills that do not match selected role.",
            details={"role_id": role_id, "invalid_skill_ids": unknown},
        )
    return loadout_skill_ids


def _list_active_members(db: Session, party_id: uuid.UUID) -> list[PartyMember]:
    stmt: Select[tuple[PartyMember]] = select(PartyMember).where(
        PartyMember.party_id == party_id,
        PartyMember.left_at.is_(None),
    )
    return list(db.execute(stmt).scalars().all())


def _to_party_out(party: Party, members: list[PartyMember]) -> PartyDetailOut:
    out_members = []
    for member in members:
        out_members.append(
            PartyMemberOut(
                player_id=member.player_id,
                role_id=member.role_id,
                loadout_skill_ids=_deserialize_skills(member.loadout_skill_ids),
                is_raid_lead=member.is_raid_lead,
            )
        )
    return PartyDetailOut(
        id=party.id,
        tavern_id=party.tavern_id,
        created_by_player_id=party.created_by_player_id,
        status=party.status,
        members=out_members,
    )


def create_party(
    db: Session,
    *,
    player_id: uuid.UUID,
    tavern_id: uuid.UUID,
    role_id: str | None,
    loadout_skill_ids: list[str] | None,
) -> PartyDetailOut:
    selected_role = role_id or DEFAULT_ROLE_ID
    selected_loadout = _validate_loadout(selected_role, loadout_skill_ids)
    now = _now()
    party = Party(
        tavern_id=tavern_id,
        created_by_player_id=player_id,
        status="open",
        created_at=now,
        updated_at=now,
    )
    db.add(party)
    db.flush()
    member = PartyMember(
        party_id=party.id,
        player_id=player_id,
        role_id=selected_role,
        loadout_skill_ids=_serialize_skills(selected_loadout),
        is_raid_lead=True,
        joined_at=now,
        left_at=None,
    )
    db.add(member)
    db.flush()
    return _to_party_out(party, [member])


def get_party(db: Session, *, party_id: uuid.UUID, player_id: uuid.UUID) -> PartyDetailOut:
    party = _get_party_or_404(db, party_id)
    members = _list_active_members(db, party_id)
    if not any(m.player_id == player_id for m in members):
        raise ApiError(
            status_code=403,
            error="party_forbidden",
            message="Player is not a member of party.",
        )
    return _to_party_out(party, members)


def join_party(
    db: Session,
    *,
    party_id: uuid.UUID,
    player_id: uuid.UUID,
    role_id: str | None,
    loadout_skill_ids: list[str] | None,
) -> PartyDetailOut:
    party = _get_party_or_404(db, party_id)
    if party.status != "open":
        raise ApiError(
            status_code=400,
            error="party_not_open",
            message="Party is not open for joining.",
        )
    existing = _get_active_member(db, party_id, player_id)
    if existing is None:
        selected_role = role_id or DEFAULT_ROLE_ID
        selected_loadout = _validate_loadout(selected_role, loadout_skill_ids)
        member = PartyMember(
            party_id=party_id,
            player_id=player_id,
            role_id=selected_role,
            loadout_skill_ids=_serialize_skills(selected_loadout),
            is_raid_lead=False,
            joined_at=_now(),
            left_at=None,
        )
        db.add(member)
        party.updated_at = _now()
        db.flush()
    members = _list_active_members(db, party_id)
    return _to_party_out(party, members)


def update_my_loadout(
    db: Session,
    *,
    party_id: uuid.UUID,
    player_id: uuid.UUID,
    role_id: str | None,
    loadout_skill_ids: list[str] | None,
) -> PartyDetailOut:
    party = _get_party_or_404(db, party_id)
    member = _get_active_member(db, party_id, player_id)
    if member is None:
        raise ApiError(
            status_code=403,
            error="party_forbidden",
            message="Player is not a member of party.",
        )
    selected_role = role_id or member.role_id
    selected_loadout = _validate_loadout(selected_role, loadout_skill_ids)
    member.role_id = selected_role
    member.loadout_skill_ids = _serialize_skills(selected_loadout)
    party.updated_at = _now()
    db.flush()
    return _to_party_out(party, _list_active_members(db, party_id))


def create_raid(
    db: Session,
    *,
    player_id: uuid.UUID,
    party_id: uuid.UUID | None,
    tavern_id: uuid.UUID | None,
    raid_template_id: str,
) -> RaidDetailOut:
    if raid_template_id not in RAID_TEMPLATES:
        raise ApiError(
            status_code=400,
            error="invalid_raid_template",
            message="Raid template is not supported in v1.",
            details={"allowed_raid_template_ids": sorted(RAID_TEMPLATES)},
        )
    selected_party_id = party_id
    if selected_party_id is None:
        if tavern_id is None:
            raise ApiError(
                status_code=400,
                error="missing_tavern_id",
                message="tavern_id is required for solo/tutorial raid creation.",
            )
        party = create_party(
            db,
            player_id=player_id,
            tavern_id=tavern_id,
            role_id=DEFAULT_ROLE_ID,
            loadout_skill_ids=list(ROLE_SKILLS[DEFAULT_ROLE_ID]),
        )
        selected_party_id = party.id
    else:
        member = _get_active_member(db, selected_party_id, player_id)
        if member is None:
            raise ApiError(
                status_code=403,
                error="party_forbidden",
                message="Only party members can start a raid.",
            )
    raid = Raid(
        party_id=selected_party_id,
        raid_template_id=raid_template_id,
        status="pending",
        started_at=None,
        ended_at=None,
    )
    db.add(raid)
    db.flush()
    return RaidDetailOut(
        id=raid.id,
        party_id=raid.party_id,
        raid_template_id=raid.raid_template_id,
        status=raid.status,
    )


def get_raid(db: Session, *, raid_id: uuid.UUID, player_id: uuid.UUID) -> RaidDetailOut:
    raid = db.get(Raid, raid_id)
    if raid is None:
        raise ApiError(status_code=404, error="raid_not_found", message="Raid was not found.")
    member = _get_active_member(db, raid.party_id, player_id)
    if member is None:
        raise ApiError(
            status_code=403,
            error="raid_forbidden",
            message="Player is not in raid party.",
        )
    return RaidDetailOut(
        id=raid.id,
        party_id=raid.party_id,
        raid_template_id=raid.raid_template_id,
        status=raid.status,
    )
