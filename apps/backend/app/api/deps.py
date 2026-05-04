"""HTTP dependencies (auth header parsing)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Header

from app.errors import ApiError


def parse_bearer_session_id(authorization: str | None) -> uuid.UUID | None:
    if not authorization or not authorization.strip():
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        return uuid.UUID(token)
    except ValueError:
        return None


def require_bearer_session_id(
    authorization: Annotated[str | None, Header()] = None,
) -> uuid.UUID:
    """Require `Authorization: Bearer <session uuid>`."""

    parsed = parse_bearer_session_id(authorization)
    if parsed is not None:
        return parsed
    if authorization and authorization.strip().startswith("Bearer"):
        raise ApiError(
            status_code=401,
            error="invalid_token",
            message="Session id in Authorization header is not a valid UUID.",
        )
    raise ApiError(
        status_code=401,
        error="missing_authorization",
        message="Authorization: Bearer <session_id> is required.",
    )
