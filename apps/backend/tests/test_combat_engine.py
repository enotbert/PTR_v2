from __future__ import annotations

import pytest
from app.services import combat_engine


def _base_payload(skill_id: str, actor_id: str, target_id: str) -> dict[str, object]:
    return {
        "skill_id": skill_id,
        "actor_entity_id": actor_id,
        "target": {"kind": "entity", "entity_id": target_id},
    }


def test_resolve_valid_enemy_target_and_apply_cooldown() -> None:
    state = combat_engine.BattleRoomState()
    actor_id = "player:1"
    payload = _base_payload("vanguard_strike", actor_id, "enemy:rustbound_striker")
    out = combat_engine.resolve_use_skill(
        payload=payload,
        actor_entity_id=actor_id,
        actor_team="ally",
        valid_entity_teams={actor_id: "ally", "enemy:rustbound_striker": "enemy"},
        state=state,
    )
    assert out.event_payload["event_type"] == "skill_resolved"
    assert out.event_payload["skill_id"] == "vanguard_strike"
    assert state.command_tick == 1
    with pytest.raises(RuntimeError):
        combat_engine.resolve_use_skill(
            payload=payload,
            actor_entity_id=actor_id,
            actor_team="ally",
            valid_entity_teams={actor_id: "ally", "enemy:rustbound_striker": "enemy"},
            state=state,
        )


def test_resolve_invalid_target_for_negative_skill() -> None:
    state = combat_engine.BattleRoomState()
    actor_id = "player:1"
    payload = _base_payload("signal_shot", actor_id, actor_id)
    with pytest.raises(ValueError, match="INVALID_TARGET"):
        combat_engine.resolve_use_skill(
            payload=payload,
            actor_entity_id=actor_id,
            actor_team="ally",
            valid_entity_teams={actor_id: "ally"},
            state=state,
        )


def test_resolve_positive_skill_allows_self_target() -> None:
    state = combat_engine.BattleRoomState()
    actor_id = "player:1"
    payload = {
        "skill_id": "mend_protocol",
        "actor_entity_id": actor_id,
        "target": {"kind": "self"},
    }
    out = combat_engine.resolve_use_skill(
        payload=payload,
        actor_entity_id=actor_id,
        actor_team="ally",
        valid_entity_teams={actor_id: "ally"},
        state=state,
    )
    assert out.event_payload["target_entity_id"] == actor_id
