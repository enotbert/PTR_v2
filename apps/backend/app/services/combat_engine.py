"""Combat validation/resolution engine for `combat.use_skill` (PTR-40)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

SkillIntent = Literal["positive", "negative"]
TargetTeam = Literal["ally", "enemy", "self"]


@dataclass(frozen=True)
class SkillSpec:
    skill_id: str
    intent: SkillIntent
    target_team: TargetTeam
    cooldown: Literal["short", "medium", "long"]
    result_type: str
    power: int


SKILLS: dict[str, SkillSpec] = {
    "vanguard_strike": SkillSpec(
        skill_id="vanguard_strike",
        intent="negative",
        target_team="enemy",
        cooldown="short",
        result_type="damage",
        power=10,
    ),
    "guard_ally": SkillSpec(
        skill_id="guard_ally",
        intent="positive",
        target_team="ally",
        cooldown="medium",
        result_type="shield",
        power=8,
    ),
    "mend_protocol": SkillSpec(
        skill_id="mend_protocol",
        intent="positive",
        target_team="ally",
        cooldown="short",
        result_type="heal",
        power=12,
    ),
    "signal_shot": SkillSpec(
        skill_id="signal_shot",
        intent="negative",
        target_team="enemy",
        cooldown="short",
        result_type="damage",
        power=9,
    ),
}

COOLDOWN_STEPS: dict[str, int] = {"short": 1, "medium": 2, "long": 3}


@dataclass(frozen=True)
class BattleSnapshotEntity:
    entity_id: str
    kind: str
    hp_current: int
    hp_max: int
    role_id: str | None = None


@dataclass
class BattleRoomState:
    phase: str = "active"
    command_tick: int = 0
    next_server_seq: int = 1
    cooldown_until_tick: dict[tuple[str, str], int] | None = None

    def __post_init__(self) -> None:
        if self.cooldown_until_tick is None:
            self.cooldown_until_tick = {}

    def issue_server_seq(self) -> int:
        value = self.next_server_seq
        self.next_server_seq += 1
        return value

    def is_skill_on_cooldown(self, actor_entity_id: str, skill_id: str) -> bool:
        until = self.cooldown_until_tick.get((actor_entity_id, skill_id), 0)
        return self.command_tick < until

    def consume_skill(self, actor_entity_id: str, spec: SkillSpec) -> None:
        self.command_tick += 1
        cooldown_steps = COOLDOWN_STEPS[spec.cooldown]
        self.cooldown_until_tick[(actor_entity_id, spec.skill_id)] = self.command_tick + cooldown_steps


@dataclass(frozen=True)
class CombatResolution:
    event_payload: dict[str, Any]


def _target_entity_id(payload: dict[str, Any], spec: SkillSpec, actor_entity_id: str) -> str:
    target = payload.get("target") or {}
    target_kind = str(target.get("kind", "")).strip()
    if spec.target_team == "enemy":
        if target_kind != "entity":
            raise ValueError("INVALID_TARGET")
        entity_id = str(target.get("entity_id", "")).strip()
        if not entity_id:
            raise ValueError("INVALID_TARGET")
        return entity_id
    if target_kind == "self":
        return actor_entity_id
    if target_kind != "entity":
        raise ValueError("INVALID_TARGET")
    entity_id = str(target.get("entity_id", "")).strip()
    if not entity_id:
        raise ValueError("INVALID_TARGET")
    return entity_id


def resolve_use_skill(
    *,
    payload: dict[str, Any],
    actor_entity_id: str,
    actor_team: str,
    valid_entity_teams: dict[str, str],
    state: BattleRoomState,
) -> CombatResolution:
    skill_id = str(payload.get("skill_id", "")).strip()
    spec = SKILLS.get(skill_id)
    if spec is None:
        raise ValueError("INVALID_PAYLOAD")

    if state.phase != "active":
        raise ValueError("INVALID_STATE")
    if state.is_skill_on_cooldown(actor_entity_id, spec.skill_id):
        raise RuntimeError("COOLDOWN_ACTIVE")

    target_entity_id = _target_entity_id(payload, spec, actor_entity_id)
    target_team = valid_entity_teams.get(target_entity_id)
    if target_team is None:
        raise ValueError("INVALID_TARGET")

    if spec.target_team == "enemy" and target_team == actor_team:
        raise ValueError("INVALID_TARGET")
    if spec.target_team in {"ally", "self"} and target_team != actor_team:
        raise ValueError("INVALID_TARGET")

    state.consume_skill(actor_entity_id, spec)
    event_payload = {
        "event_type": "skill_resolved",
        "skill_id": spec.skill_id,
        "actor_entity_id": actor_entity_id,
        "target_entity_id": target_entity_id,
        "result_type": spec.result_type,
        "value": spec.power,
        "tick": state.command_tick,
    }
    return CombatResolution(event_payload=event_payload)
