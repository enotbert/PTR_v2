"""Player / session REST API (v1)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_bearer_session_id
from app.db import get_db
from app.schemas.session import CreateSessionBody, ErrorBody, PlayerOut, SessionEnvelope, SessionOut
from app.services import session as session_service

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


@router.post(
    "/sessions",
    response_model=SessionEnvelope,
    status_code=201,
    responses={
        401: {"model": ErrorBody, "description": "Session expired or revoked (resume only)"},
        404: {"model": ErrorBody, "description": "Session not found (resume only)"},
    },
)
def create_or_resume_session(
    request: Request,
    body: CreateSessionBody,
    db: Annotated[Session, Depends(get_db)],
) -> SessionEnvelope:
    last_ip = _client_ip(request)
    ua = request.headers.get("user-agent")
    if body.resume_session_id is not None:
        player, row = session_service.resume_session(
            db,
            body.resume_session_id,
            last_ip=last_ip,
            last_user_agent=ua,
        )
    else:
        player, row = session_service.create_new_session(
            db,
            display_name=body.display_name,
            device_fingerprint=body.device_fingerprint,
            last_ip=last_ip,
            last_user_agent=ua,
        )
    return SessionEnvelope(
        player=PlayerOut.model_validate(player),
        session=SessionOut.model_validate(row),
    )


@router.get(
    "/sessions/current",
    response_model=SessionEnvelope,
    responses={
        401: {"model": ErrorBody},
        404: {"model": ErrorBody},
    },
)
def get_current_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    session_id: Annotated[uuid.UUID, Depends(require_bearer_session_id)],
) -> SessionEnvelope:
    player, row = session_service.resume_session(
        db,
        session_id,
        last_ip=_client_ip(request),
        last_user_agent=request.headers.get("user-agent"),
    )
    return SessionEnvelope(
        player=PlayerOut.model_validate(player),
        session=SessionOut.model_validate(row),
    )
