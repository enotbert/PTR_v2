"""Minimal FastAPI app for Docker dev stack scaffold (PTR-17)."""

import os

import psycopg
from fastapi import FastAPI

DATABASE_URL = os.environ.get("DATABASE_URL", "")

app = FastAPI(title="PTR backend (dev scaffold)", version="0.0.0")


@app.get("/")
def root() -> dict:
    return {"service": "backend", "docs": "/docs"}


@app.get("/health")
def health() -> dict:
    """Uvicorn liveness plus Postgres reachability via compose network."""

    if not DATABASE_URL.strip():
        return {"status": "degraded", "postgres": "missing_database_url"}
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
            conn.execute("SELECT 1")
    except Exception:
        return {"status": "degraded", "postgres": "unreachable"}
    return {"status": "ok", "postgres": "reachable"}
