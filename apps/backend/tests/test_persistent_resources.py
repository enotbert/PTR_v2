"""Smoke tests for v1 persistent resource skeleton routes and OpenAPI paths."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.models.identity import Player, PlayerSession
from fastapi.testclient import TestClient


@pytest.fixture
def authed_client(session_client: TestClient, db_session) -> tuple[TestClient, uuid.UUID, str]:
    now = datetime.now(UTC)
    exp = now + timedelta(days=30)
    p = Player(
        display_name="ApiSkel",
        created_at=now,
        updated_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add(p)
    db_session.flush()
    s = PlayerSession(
        player_id=p.id,
        issued_at=now,
        expires_at=exp,
    )
    db_session.add(s)
    db_session.commit()
    auth = f"Bearer {s.id}"
    return session_client, p.id, auth


def test_openapi_lists_persistent_paths(session_client: TestClient) -> None:
    r = session_client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/v1/taverns/{tavern_id}/state" in paths
    assert "/v1/taverns/{tavern_id}/contributions" in paths
    assert "/v1/parties/{party_id}" in paths
    assert "/v1/parties" in paths
    assert "/v1/parties/{party_id}/join" in paths
    assert "/v1/parties/{party_id}/members/me/loadout" in paths
    assert "/v1/raids/{raid_id}" in paths
    assert "/v1/raids" in paths
    assert "/v1/players/me/rewards" in paths
    assert "/v1/rewards/{reward_id}/claims" in paths
    assert "/v1/invites" in paths
    assert "/v1/invites/by-token/{token}" in paths
    assert "/v1/analytics/debug/recent-events" in paths


def test_get_tavern_state_placeholder(authed_client: tuple[TestClient, uuid.UUID, str]) -> None:
    client, player_id, auth = authed_client
    tid = uuid.uuid4()
    r = client.get(f"/v1/taverns/{tid}/state", headers={"Authorization": auth})
    assert r.status_code == 200
    body = r.json()
    assert body["tavern_id"] == str(tid)
    assert body["player_id"] == str(player_id)
    assert body["reputation"] == 0
    assert body["weekly_points"] == 0
    assert body["current_project"]["id"] == "weekly_route_reopening"
    assert body["contribution_summary"]["total_points"] == 0
    assert body["chronicle"] == []


def test_post_tavern_contribution_updates_state(
    authed_client: tuple[TestClient, uuid.UUID, str],
) -> None:
    client, player_id, auth = authed_client
    tavern_id = uuid.uuid4()
    add = client.post(
        f"/v1/taverns/{tavern_id}/contributions",
        headers={"Authorization": auth},
        json={"amount": 25, "source_type": "raid_reward", "source_ref": "raid-001"},
    )
    assert add.status_code == 200
    added = add.json()
    assert added["player_id"] == str(player_id)
    assert added["tavern_id"] == str(tavern_id)
    assert added["weekly_points"] == 25
    assert added["reputation"] == 25
    assert added["contribution_summary"]["latest_amount"] == 25
    assert added["contribution_summary"]["latest_source_type"] == "raid_reward"
    assert len(added["chronicle"]) == 1
    assert added["chronicle"][0]["amount"] == 25

    read = client.get(f"/v1/taverns/{tavern_id}/state", headers={"Authorization": auth})
    assert read.status_code == 200
    state = read.json()
    assert state["weekly_points"] == 25
    assert state["reputation"] == 25
    assert state["contribution_summary"]["total_points"] == 25


def test_post_tavern_contribution_rejects_out_of_bounds_amount(
    authed_client: tuple[TestClient, uuid.UUID, str],
) -> None:
    client, _, auth = authed_client
    tavern_id = uuid.uuid4()

    zero = client.post(
        f"/v1/taverns/{tavern_id}/contributions",
        headers={"Authorization": auth},
        json={"amount": 0, "source_type": "raid_reward"},
    )
    assert zero.status_code == 422

    too_large = client.post(
        f"/v1/taverns/{tavern_id}/contributions",
        headers={"Authorization": auth},
        json={"amount": 10001, "source_type": "raid_reward"},
    )
    assert too_large.status_code == 422


def test_create_party_with_default_vanguard_loadout(
    authed_client: tuple[TestClient, uuid.UUID, str],
) -> None:
    client, player_id, auth = authed_client
    tavern_id = uuid.uuid4()
    r = client.post(
        "/v1/parties",
        headers={"Authorization": auth},
        json={"tavern_id": str(tavern_id), "role_id": "vanguard"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tavern_id"] == str(tavern_id)
    assert body["created_by_player_id"] == str(player_id)
    assert body["status"] == "open"
    assert len(body["members"]) == 1
    assert body["members"][0]["player_id"] == str(player_id)
    assert body["members"][0]["role_id"] == "vanguard"
    assert body["members"][0]["loadout_skill_ids"] == [
        "vanguard_strike",
        "guard_ally",
        "taunt_signal",
    ]
    assert body["members"][0]["is_raid_lead"] is True


def test_join_party_and_update_my_loadout(
    session_client: TestClient,
    db_session,
) -> None:
    now = datetime.now(UTC)
    exp = now + timedelta(days=30)
    owner = Player(
        display_name="Owner",
        created_at=now,
        updated_at=now,
        last_seen_at=now,
        is_active=True,
    )
    joiner = Player(
        display_name="Joiner",
        created_at=now,
        updated_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add_all([owner, joiner])
    db_session.flush()
    owner_session = PlayerSession(player_id=owner.id, issued_at=now, expires_at=exp)
    joiner_session = PlayerSession(player_id=joiner.id, issued_at=now, expires_at=exp)
    db_session.add_all([owner_session, joiner_session])
    db_session.commit()

    tavern_id = uuid.uuid4()
    create_party = session_client.post(
        "/v1/parties",
        headers={"Authorization": f"Bearer {owner_session.id}"},
        json={"tavern_id": str(tavern_id), "role_id": "vanguard"},
    )
    assert create_party.status_code == 200
    party_id = create_party.json()["id"]

    joined = session_client.post(
        f"/v1/parties/{party_id}/join",
        headers={"Authorization": f"Bearer {joiner_session.id}"},
        json={
            "role_id": "arcweaver",
            "loadout_skill_ids": ["arc_bolt", "rune_overload", "phase_disrupt"],
        },
    )
    assert joined.status_code == 200
    joined_body = joined.json()
    assert len(joined_body["members"]) == 2
    joiner_member = next(
        member for member in joined_body["members"] if member["player_id"] == str(joiner.id)
    )
    assert joiner_member["role_id"] == "arcweaver"

    updated = session_client.patch(
        f"/v1/parties/{party_id}/members/me/loadout",
        headers={"Authorization": f"Bearer {joiner_session.id}"},
        json={"role_id": "signal_bard"},
    )
    assert updated.status_code == 200
    updated_joiner_member = next(
        member
        for member in updated.json()["members"]
        if member["player_id"] == str(joiner.id)
    )
    assert updated_joiner_member["role_id"] == "signal_bard"
    assert updated_joiner_member["loadout_skill_ids"] == [
        "signal_shot",
        "mark_target",
        "rally_chord",
    ]


def test_create_party_rejects_invalid_loadout_skill(
    authed_client: tuple[TestClient, uuid.UUID, str],
) -> None:
    client, _, auth = authed_client
    tavern_id = uuid.uuid4()
    r = client.post(
        "/v1/parties",
        headers={"Authorization": auth},
        json={
            "tavern_id": str(tavern_id),
            "role_id": "vanguard",
            "loadout_skill_ids": ["vanguard_strike", "arc_bolt", "taunt_signal"],
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["error"] == "invalid_loadout_skill"


def test_create_raid_from_tutorial_solo_flow(
    authed_client: tuple[TestClient, uuid.UUID, str],
) -> None:
    client, _, auth = authed_client
    tavern_id = uuid.uuid4()
    created = client.post(
        "/v1/raids",
        headers={"Authorization": auth},
        json={"tavern_id": str(tavern_id), "raid_template_id": "tutorial_solo_v1"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["raid_template_id"] == "tutorial_solo_v1"
    assert body["status"] == "pending"
    read = client.get(f"/v1/raids/{body['id']}", headers={"Authorization": auth})
    assert read.status_code == 200


def test_create_raid_rejects_non_member_start_for_party(
    session_client: TestClient,
    db_session,
) -> None:
    now = datetime.now(UTC)
    exp = now + timedelta(days=30)
    owner = Player(
        display_name="Owner2",
        created_at=now,
        updated_at=now,
        last_seen_at=now,
        is_active=True,
    )
    outsider = Player(
        display_name="Outsider",
        created_at=now,
        updated_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add_all([owner, outsider])
    db_session.flush()
    owner_session = PlayerSession(player_id=owner.id, issued_at=now, expires_at=exp)
    outsider_session = PlayerSession(player_id=outsider.id, issued_at=now, expires_at=exp)
    db_session.add_all([owner_session, outsider_session])
    db_session.commit()

    tavern_id = uuid.uuid4()
    created_party = session_client.post(
        "/v1/parties",
        headers={"Authorization": f"Bearer {owner_session.id}"},
        json={"tavern_id": str(tavern_id), "role_id": "vanguard"},
    )
    assert created_party.status_code == 200
    party_id = created_party.json()["id"]

    raid = session_client.post(
        "/v1/raids",
        headers={"Authorization": f"Bearer {outsider_session.id}"},
        json={"party_id": party_id, "raid_template_id": "regular_party_v1"},
    )
    assert raid.status_code == 403
    assert raid.json()["error"] == "party_forbidden"


def test_get_invite_by_token_shape(session_client: TestClient) -> None:
    r = session_client.get("/v1/invites/by-token/demo-token")
    assert r.status_code == 200
    assert r.json()["token"] == "demo-token"
