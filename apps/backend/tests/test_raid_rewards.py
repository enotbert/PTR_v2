from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.game_audit_event import GameAuditEvent
from app.models.identity import Player, PlayerSession
from app.models.party_raid import Party, PartyMember
from app.models.tavern import TavernContribution
from app.services import raid_rewards


def _make_player(db_session, name: str) -> tuple[uuid.UUID, uuid.UUID]:
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
        expires_at=now,
    )
    db_session.add(session)
    db_session.flush()
    return player.id, session.id


def _create_party_with_members(db_session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    owner_id, owner_session_id = _make_player(db_session, "Owner")
    joiner_id, _ = _make_player(db_session, "Joiner")
    now = datetime.now(UTC)
    party = Party(
        tavern_id=uuid.uuid4(),
        created_by_player_id=owner_id,
        status="open",
        created_at=now,
        updated_at=now,
    )
    db_session.add(party)
    db_session.flush()
    db_session.add(
        PartyMember(
            party_id=party.id,
            player_id=owner_id,
            role_id="vanguard",
            loadout_skill_ids="[]",
            is_raid_lead=True,
            joined_at=now,
            left_at=None,
        )
    )
    db_session.add(
        PartyMember(
            party_id=party.id,
            player_id=joiner_id,
            role_id="signal_bard",
            loadout_skill_ids="[]",
            is_raid_lead=False,
            joined_at=now,
            left_at=None,
        )
    )
    db_session.flush()
    return party.id, owner_id, owner_session_id, joiner_id


def test_resolve_raid_rewards_is_idempotent_for_repeated_calls(db_session) -> None:
    party_id, owner_id, owner_session_id, joiner_id = _create_party_with_members(db_session)

    first = raid_rewards.resolve_raid_outcome_and_issue_rewards(
        db_session,
        party_id=party_id,
        enemies_defeated=True,
        allies_defeated=False,
        approved_failed_progress=False,
        triggered_by_player_id=owner_id,
        session_id=owner_session_id,
    )
    second = raid_rewards.resolve_raid_outcome_and_issue_rewards(
        db_session,
        party_id=party_id,
        enemies_defeated=True,
        allies_defeated=False,
        approved_failed_progress=False,
        triggered_by_player_id=owner_id,
        session_id=owner_session_id,
    )

    assert first.claim_status == "claimed"
    assert second.claim_status == "already_claimed"
    assert len(first.newly_issued_reward_record_ids) == 2
    assert len(second.newly_issued_reward_record_ids) == 0
    assert sorted(first.reward_record_ids) == sorted(second.reward_record_ids)

    reward_rows = (
        db_session.query(TavernContribution)
        .filter(TavernContribution.source_type == "raid_reward")
        .all()
    )
    assert len(reward_rows) == 2
    assert {row.player_id for row in reward_rows} == {owner_id, joiner_id}

    audit_rows = (
        db_session.query(GameAuditEvent)
        .filter(GameAuditEvent.event_name == "raid.outcome_resolved")
        .order_by(GameAuditEvent.event_at.asc())
        .all()
    )
    assert len(audit_rows) == 2
    assert audit_rows[0].payload_json["claim_status"] == "claimed"
    assert audit_rows[1].payload_json["claim_status"] == "already_claimed"


def test_resolve_raid_rewards_rejects_player_not_in_party(db_session) -> None:
    party_id, _, _, _ = _create_party_with_members(db_session)
    outsider_id, outsider_session_id = _make_player(db_session, "Outsider")

    try:
        raid_rewards.resolve_raid_outcome_and_issue_rewards(
            db_session,
            party_id=party_id,
            enemies_defeated=True,
            allies_defeated=False,
            approved_failed_progress=False,
            triggered_by_player_id=outsider_id,
            session_id=outsider_session_id,
        )
    except ValueError as exc:
        assert str(exc) == "PLAYER_NOT_IN_PARTY"
    else:
        raise AssertionError("Expected PLAYER_NOT_IN_PARTY")


def test_resolve_raid_rewards_rejects_unknown_party(db_session) -> None:
    player_id, session_id = _make_player(db_session, "Any")

    try:
        raid_rewards.resolve_raid_outcome_and_issue_rewards(
            db_session,
            party_id=uuid.uuid4(),
            enemies_defeated=True,
            allies_defeated=False,
            approved_failed_progress=False,
            triggered_by_player_id=player_id,
            session_id=session_id,
        )
    except ValueError as exc:
        assert str(exc) == "PARTY_NOT_FOUND"
    else:
        raise AssertionError("Expected PARTY_NOT_FOUND")
