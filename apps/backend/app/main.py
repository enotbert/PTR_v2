"""FastAPI backend baseline with health and OpenAPI endpoints."""

import os

import psycopg
from fastapi import APIRouter, FastAPI

router = APIRouter()


def create_app() -> FastAPI:
    app = FastAPI(
        title="PTR backend",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        redoc_url=None,
    )
    app.include_router(router)
    return app


@router.get("/")
def root() -> dict:
    return {"service": "backend", "docs": "/docs"}


@router.get("/health")
def health() -> dict:
    """Uvicorn liveness plus Postgres reachability via compose network."""

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        return {"status": "degraded", "postgres": "missing_database_url"}
    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn:
            conn.execute("SELECT 1")
    except psycopg.Error:
        return {"status": "degraded", "postgres": "unreachable"}
    return {"status": "ok", "postgres": "reachable"}


app = create_app()
