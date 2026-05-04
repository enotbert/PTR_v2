"""Smoke tests for FastAPI health and root routes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "backend"


def test_health_without_database_url(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "postgres": "missing_database_url"}


@patch("app.main.psycopg.connect")
def test_health_postgres_reachable(
    mock_connect: MagicMock, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@postgres:5432/db")
    cm = MagicMock()
    conn = MagicMock()
    cm.__enter__.return_value = conn
    cm.__exit__.return_value = None
    mock_connect.return_value = cm

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "postgres": "reachable"}
    mock_connect.assert_called_once()
