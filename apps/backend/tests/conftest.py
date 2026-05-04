"""Pytest fixtures: in-memory SQLite + dependency overrides for API tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db import get_db, init_metadata_for_tests
from app.main import create_app
from app.models.identity import Player, PlayerSession
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sqlite_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_metadata_for_tests(engine)
    return engine


@pytest.fixture
def session_client(sqlite_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def db_session(sqlite_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
    s = SessionLocal()
    try:
        yield s
        s.commit()
    finally:
        s.close()


@pytest.fixture
def db_player_id(db_session) -> uuid.UUID:
    now = datetime.now(UTC)
    p = Player(
        display_name="FixturePlayer",
        created_at=now,
        updated_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add(p)
    db_session.flush()
    return p.id


@pytest.fixture
def db_player_session_ids(db_session) -> tuple[uuid.UUID, uuid.UUID]:
    now = datetime.now(UTC)
    exp = now + timedelta(days=30)
    p = Player(
        display_name="FixturePlayer2",
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
    db_session.flush()
    return p.id, s.id
