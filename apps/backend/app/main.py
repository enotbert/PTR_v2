"""FastAPI backend: health, OpenAPI, and v1 session API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import psycopg
from fastapi import APIRouter, FastAPI

from app.api.v1.lobby_ws import router as lobby_ws_router
from app.api.v1.persistent_resources import router as persistent_resources_router
from app.api.v1.sessions import router as sessions_router
from app.errors import ApiError, api_error_handler

router = APIRouter()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        from app.db import configure_engine

        configure_engine(url)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="PTR backend",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router)
    app.include_router(sessions_router, prefix="/v1")
    app.include_router(persistent_resources_router, prefix="/v1")
    app.include_router(lobby_ws_router, prefix="/v1")
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
