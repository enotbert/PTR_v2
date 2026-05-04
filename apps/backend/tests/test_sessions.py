"""Tests for v1 player/session API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.identity import PlayerSession
from fastapi.testclient import TestClient


def test_openapi_includes_session_routes(session_client: TestClient) -> None:
    r = session_client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/v1/sessions" in paths
    assert "/v1/sessions/current" in paths


def test_create_session_new_player(session_client: TestClient) -> None:
    r = session_client.post(
        "/v1/sessions",
        json={"display_name": "Tester", "device_fingerprint": "dev-1"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["player"]["display_name"] == "Tester"
    assert data["player"]["is_active"] is True
    assert "id" in data["session"] and "id" in data["player"]
    assert data["session"]["player_id"] == data["player"]["id"]


def test_create_session_default_name(session_client: TestClient) -> None:
    r = session_client.post("/v1/sessions", json={})
    assert r.status_code == 201
    assert r.json()["player"]["display_name"] == "Adventurer"


def test_resume_session(session_client: TestClient) -> None:
    created = session_client.post(
        "/v1/sessions",
        json={"display_name": "ResumeMe"},
    ).json()
    sid = created["session"]["id"]
    r = session_client.post(
        "/v1/sessions",
        json={"resume_session_id": sid},
    )
    assert r.status_code == 201
    assert r.json()["player"]["id"] == created["player"]["id"]
    assert r.json()["session"]["id"] == sid


def test_resume_unknown_session(session_client: TestClient) -> None:
    r = session_client.post(
        "/v1/sessions",
        json={"resume_session_id": "00000000-0000-0000-0000-000000000099"},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "session_not_found"


def test_get_current_session(session_client: TestClient) -> None:
    created = session_client.post("/v1/sessions", json={}).json()
    sid = created["session"]["id"]
    r = session_client.get(
        "/v1/sessions/current",
        headers={"Authorization": f"Bearer {sid}"},
    )
    assert r.status_code == 200
    assert r.json()["session"]["id"] == sid


def test_get_current_missing_auth(session_client: TestClient) -> None:
    r = session_client.get("/v1/sessions/current")
    assert r.status_code == 401
    assert r.json()["error"] == "missing_authorization"


def test_get_current_invalid_token(session_client: TestClient) -> None:
    r = session_client.get(
        "/v1/sessions/current",
        headers={"Authorization": "Bearer not-a-uuid"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_token"


def test_session_expired(session_client: TestClient, db_session) -> None:
    created = session_client.post("/v1/sessions", json={}).json()
    sid = created["session"]["id"]
    row = db_session.get(PlayerSession, uuid.UUID(sid))
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(days=1)
    db_session.add(row)
    db_session.commit()

    r = session_client.get(
        "/v1/sessions/current",
        headers={"Authorization": f"Bearer {sid}"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "session_expired"


def test_session_revoked(session_client: TestClient, db_session) -> None:
    created = session_client.post("/v1/sessions", json={}).json()
    sid = created["session"]["id"]
    row = db_session.get(PlayerSession, uuid.UUID(sid))
    assert row is not None
    row.revoked_at = datetime.now(UTC)
    db_session.add(row)
    db_session.commit()

    r = session_client.get(
        "/v1/sessions/current",
        headers={"Authorization": f"Bearer {sid}"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "session_revoked"
