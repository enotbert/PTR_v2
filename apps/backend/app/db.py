"""Database engine and session factory (DATABASE_URL from environment)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.errors import ApiError
from app.models import Base  # noqa: F401 — register models

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql+psycopg"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def configure_engine(url: str) -> Engine:
    """Create engine (used by app lifespan and tests)."""

    global _engine, _SessionLocal
    normalized = normalize_database_url(url.strip())
    _engine = create_engine(normalized, pool_pre_ping=True)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        msg = "Database engine is not configured"
        raise RuntimeError(msg)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        msg = "Database session factory is not configured"
        raise RuntimeError(msg)
    return _SessionLocal


def get_db() -> Generator[Session]:
    """FastAPI dependency: one request-scoped SQLAlchemy session."""

    try:
        factory = get_session_factory()
    except RuntimeError as exc:
        raise ApiError(
            status_code=503,
            error="database_unavailable",
            message="Database is not configured (DATABASE_URL missing or engine not started).",
        ) from exc
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_metadata_for_tests(engine: Engine) -> None:
    """Create tables from models (SQLite tests only; production uses Alembic)."""

    Base.metadata.create_all(bind=engine)
