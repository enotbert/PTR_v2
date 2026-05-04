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
    assert "/v1/parties/{party_id}" in paths
    assert "/v1/parties" in paths
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


def test_create_party_not_implemented(authed_client: tuple[TestClient, uuid.UUID, str]) -> None:
    client, _, auth = authed_client
    r = client.post("/v1/parties", headers={"Authorization": auth})
    assert r.status_code == 501
    err = r.json()
    assert err["error"] == "not_implemented"
    assert err["details"]["tracked_by"] == "PTR-37"


def test_get_invite_by_token_shape(session_client: TestClient) -> None:
    r = session_client.get("/v1/invites/by-token/demo-token")
    assert r.status_code == 200
    assert r.json()["token"] == "demo-token"
