"""Fail fast if ORM metadata tables are missing in the DB after migrations."""

from __future__ import annotations

import os

from app.db import normalize_database_url
from app.models import Base  # noqa: F401  # imports models for metadata registration
from sqlalchemy import create_engine, inspect


def main() -> int:
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if not raw_url:
        print("ERROR: DATABASE_URL is not set.")
        return 1

    engine = create_engine(normalize_database_url(raw_url), pool_pre_ping=True)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())

    missing = sorted(expected_tables - existing_tables)
    if missing:
        print("ERROR: database schema is missing ORM tables after alembic upgrade head:")
        for table in missing:
            print(f" - {table}")
        return 1

    print("OK: database schema includes all ORM metadata tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
