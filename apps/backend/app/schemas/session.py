"""Pydantic schemas for session API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
    is_active: bool


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    player_id: uuid.UUID
    issued_at: datetime
    expires_at: datetime
    device_fingerprint: str | None = None


class SessionEnvelope(BaseModel):
    player: PlayerOut
    session: SessionOut


class CreateSessionBody(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    device_fingerprint: str | None = Field(default=None, max_length=256)
    resume_session_id: uuid.UUID | None = None


class ErrorBody(BaseModel):
    error: str
    message: str
    details: dict[str, object] | None = None
