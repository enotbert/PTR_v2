"""Minimal FastAPI app for Docker dev stack (PTR-17 scaffold, PTR-18 uv/pytest)."""

import os

import psycopg
from fastapi import FastAPI

app = FastAPI(title="PTR backend (dev scaffold)", version="0.0.0")


@app.get("/")
def root() -> dict:
    return {"service": "backend", "docs": "/docs"}


@app.get("/health")
def health() -> dict:
    """Uvicorn liveness plus Postgres reachability via compose network."""

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        return {"status": "degraded", "postgres": "missing_database_url"}
    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn:
            conn.execute("SELECT 1")
    except Exception:
        return {"status": "degraded", "postgres": "unreachable"}
    return {"status": "ok", "postgres": "reachable"}
