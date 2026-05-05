"""Pydantic schemas for v1 persistent resource REST skeleton (OpenAPI-stable names)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TavernRefOut(BaseModel):
    """Public tavern reference (read model boundary)."""

    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    slug: str
    name: str
    tier: int = 0


class PlayerTavernStateOut(BaseModel):
    """Per-player tavern progression snapshot (authority: ``player_tavern_state``)."""

    model_config = ConfigDict(from_attributes=False)

    tavern_id: uuid.UUID
    player_id: uuid.UUID
    reputation: int = 0
    weekly_points: int = 0
    updated_at: datetime
    current_project: TavernProjectOut
    contribution_summary: TavernContributionSummaryOut
    chronicle: list[TavernChronicleEntryOut] = Field(default_factory=list)


class TavernProjectOut(BaseModel):
    id: str
    title: str
    status: Literal["active", "completed", "reward_claimable", "expired"] = "active"
    progress_points: int = 0
    target_points: int = 0


class TavernContributionSummaryOut(BaseModel):
    total_points: int = 0
    latest_amount: int | None = None
    latest_source_type: str | None = None
    latest_at: datetime | None = None


class TavernChronicleEntryOut(BaseModel):
    id: uuid.UUID
    source_type: str
    source_ref: str | None = None
    amount: int
    created_at: datetime


class AddTavernContributionBody(BaseModel):
    amount: int = Field(gt=0, le=10_000)
    source_type: Literal["raid_reward", "weekly_event", "manual_spend"] = "raid_reward"
    source_ref: str | None = Field(default=None, max_length=128)


class PartyMemberOut(BaseModel):
    player_id: uuid.UUID
    role_id: str
    loadout_skill_ids: list[str] = Field(default_factory=list, min_length=3, max_length=3)
    is_raid_lead: bool = False


class PartyDetailOut(BaseModel):
    id: uuid.UUID
    tavern_id: uuid.UUID
    created_by_player_id: uuid.UUID
    status: Literal["open", "locked", "in_raid", "archived"] = "open"
    members: list[PartyMemberOut] = Field(default_factory=list)


class PartyCreateBody(BaseModel):
    tavern_id: uuid.UUID
    role_id: str = "vanguard"
    loadout_skill_ids: list[str] | None = Field(default=None, min_length=3, max_length=3)


class PartyJoinBody(BaseModel):
    role_id: str = "vanguard"
    loadout_skill_ids: list[str] | None = Field(default=None, min_length=3, max_length=3)


class PartyLoadoutPatchBody(BaseModel):
    role_id: str | None = None
    loadout_skill_ids: list[str] | None = Field(default=None, min_length=3, max_length=3)


class RaidDetailOut(BaseModel):
    id: uuid.UUID
    party_id: uuid.UUID
    raid_template_id: str = "unknown"
    status: Literal["pending", "active", "completed", "failed", "abandoned"] = "pending"


class RaidCreateBody(BaseModel):
    party_id: uuid.UUID | None = None
    tavern_id: uuid.UUID | None = None
    raid_template_id: Literal["tutorial_solo_v1", "regular_party_v1"] = "tutorial_solo_v1"


class RewardItemOut(BaseModel):
    id: uuid.UUID
    player_id: uuid.UUID
    raid_id: uuid.UUID | None = None
    reward_type: Literal["loot", "weekly", "invite_bonus"] = "loot"
    created_at: datetime


class RewardListOut(BaseModel):
    items: list[RewardItemOut] = Field(default_factory=list)


class InviteDetailOut(BaseModel):
    id: uuid.UUID
    created_by_player_id: uuid.UUID
    raid_id: uuid.UUID | None = None
    token: str
    status: Literal["active", "used", "expired", "revoked"] = "active"
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None


class AnalyticsDebugEventOut(BaseModel):
    id: uuid.UUID
    event_name: str
    player_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    raid_id: uuid.UUID | None = None
    battle_id: uuid.UUID | None = None
    event_at: datetime


class AnalyticsDebugEventListOut(BaseModel):
    items: list[AnalyticsDebugEventOut] = Field(default_factory=list)


__all__ = [
    "AddTavernContributionBody",
    "AnalyticsDebugEventListOut",
    "AnalyticsDebugEventOut",
    "PartyCreateBody",
    "TavernChronicleEntryOut",
    "TavernContributionSummaryOut",
    "InviteDetailOut",
    "PartyDetailOut",
    "PartyJoinBody",
    "PartyLoadoutPatchBody",
    "PartyMemberOut",
    "PlayerTavernStateOut",
    "RaidCreateBody",
    "RaidDetailOut",
    "RewardItemOut",
    "RewardListOut",
    "TavernProjectOut",
    "TavernRefOut",
]
