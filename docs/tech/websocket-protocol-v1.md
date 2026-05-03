# WebSocket protocol v1 — lobby and battle

Статус: accepted v0.1.

Связано с: [PRD v1](../product/PRD_v1_public_early_access.md), [ADR-0007](../adr/0007-minimal-roles-and-skills-v1.md),
[Enemy roster v1](../product/enemy_roster_v1.md), [Weekly event v1](../product/weekly_event_v1.md).

## 0. Роль документа

Этот документ фиксирует минимальный WebSocket contract для public EA v1:

- lobby state без manual refresh;
- battle snapshots/events;
- client commands для skill intent, raid lead commands, emoji, quick phrases и ready/status;
- structured `command.result` / `command.error`;
- `server_seq`, `client_command_id`, idempotency и reconnect через fresh snapshot.

Документ не реализует WebSocket server/client, не задаёт конкретную backend-библиотеку и не заменяет REST/OpenAPI
для обычных API.

## 1. Scope guard

WebSocket v1 используется только для live lobby/combat. REST/OpenAPI остаётся контрактом для auth/session bootstrap,
profile, inventory, rewards claim, tavern progress и share flows.

Не входит в v1:

- свободный текстовый чат в бою;
- произвольные user-generated messages в payload;
- offline action queue;
- delta replay после reconnect;
- PvP, spectators, moderation tools и full MMO presence;
- client-authoritative combat outcome.

## 2. Transport and envelope

V1 assumes one authenticated WebSocket connection per active client session. Concrete URL shape is an implementation
detail, but downstream tasks should preserve two logical rooms:

```text
lobby room  -> ptr.ws.v1/lobbies/{lobby_id}
battle room -> ptr.ws.v1/battles/{battle_id}
```

All messages use a JSON envelope:

```json
{
  "protocol": "ptr.ws.v1",
  "kind": "command",
  "type": "combat.use_skill",
  "room": { "kind": "battle", "id": "battle_01H..." },
  "client_command_id": "cmd_01H...",
  "sent_at": "2026-05-03T20:00:00.000Z",
  "payload": {}
}
```

| Field | Direction | Required | Notes |
|---|---|---:|---|
| `protocol` | both | yes | Always `ptr.ws.v1`. |
| `kind` | both | yes | `command`, `snapshot`, `event`, `result`, `error`, `heartbeat`. |
| `type` | both | yes | Stable message name from this document. |
| `room.kind` | both | yes | `lobby` or `battle`. |
| `room.id` | both | yes | `lobby_id` or `battle_id`. |
| `server_seq` | server -> client | yes for snapshots/events/results/errors | Monotonic per room. |
| `client_command_id` | client -> server | yes for commands | Idempotency key, echoed in result/error. |
| `sent_at` | both | yes | Sender timestamp; not authoritative for ordering. |
| `payload` | both | yes | Message-specific object. |

Ordering is defined only by `server_seq`, not by wall-clock time.

## 3. Sequence and reconnect

`server_seq` is scoped to one room and strictly increases for every authoritative server message:
`lobby.snapshot`, `lobby.event`, `battle.snapshot`, `battle.event`, `command.result`, `command.error`.

Client behavior:

- keep `last_applied_server_seq` per room;
- apply snapshot and replace local room state, then set `last_applied_server_seq = snapshot.server_seq`;
- apply event/result/error only if `server_seq > last_applied_server_seq`;
- ignore duplicates where `server_seq <= last_applied_server_seq`;
- if `server_seq > last_applied_server_seq + 1`, reconnect and wait for a fresh snapshot.

V1 reconnect always resolves through a fresh snapshot:

1. Client detects closed socket, heartbeat timeout or sequence gap.
2. Client enters reconnecting UI state and stops applying optimistic local changes.
3. Client rejoins the same logical room with optional `last_seen_server_seq`.
4. Server authenticates, verifies room access and sends current `lobby.snapshot` or `battle.snapshot`.
5. Client replaces local state with the snapshot.
6. Client may retry pending commands only with the same `client_command_id`.

V1 does not require event backfill/replay. `last_seen_server_seq` is useful for logs/metrics only.

## 4. Idempotency

Every client command must include a stable `client_command_id` for one user intent. Recommended format: ULID/UUID with
a `cmd_` prefix for logs.

Server idempotency key:

```text
(player_id, room.kind, room.id, client_command_id)
```

Server behavior:

- first valid command with a new id is validated and either accepted or rejected;
- duplicate command with the same id and same semantic payload returns a new result/error referencing the original
  outcome, without applying side effects again;
- duplicate id with a different semantic payload returns `command.error` with `code = "IDEMPOTENCY_CONFLICT"`;
- dedupe history must live at least for the active lobby/battle lifetime.

## 5. Client commands

### `lobby.set_player_status`

Updates player readiness/presence before battle starts.

Payload:

| Field | Type | Required | Values |
|---|---|---:|---|
| `status` | string | yes | `not_ready`, `ready`, `away` |

Server response: `command.result` and, when visible state changes, `lobby.event` with
`event_type = "player_status_changed"`.

### `combat.use_skill`

Requests a combat skill intent. Backend validates target, cooldown, combat phase and authoritative outcome.

Payload:

| Field | Type | Required | Notes |
|---|---|---:|---|
| `skill_id` | string | yes | Stable skill id from ADR-0007. |
| `actor_entity_id` | string | yes | Entity controlled by the player. |
| `target.kind` | string | yes | `entity`, `group`, `self`, `none`. |
| `target.entity_id` | string | for `entity` | Target entity. |
| `target.group_id` | string | for `group` | Backend-defined group target. |

Target rules:

- negative skills target enemies unless future skill metadata says otherwise;
- positive skills target allies, with self allowed where ADR-0007 permits it;
- invalid target returns `command.error` with `code = "INVALID_TARGET"`;
- PixiJS/React may show target hints but never calculates authoritative result.

Server response: `command.result` when accepted, then one or more `battle.event` messages for actual outcome.

### `combat.send_raid_lead_command`

Sends a predefined raid lead command. Only the current raid lead or server-approved substitute may send it.

Payload:

| Field | Type | Required | Values |
|---|---|---:|---|
| `command_id` | string | yes | `focus_target`, `interrupt_channel`, `break_link`, `hold_defense`, `rally` |
| `target.kind` | string | for targeted commands | `entity` |
| `target.entity_id` | string | for targeted commands | Enemy/boss entity id |

Targeted commands:

- `focus_target`
- `interrupt_channel`
- `break_link`

Server response: `command.result`, then `battle.event` with `event_type = "raid_lead_command_sent"`.

### `combat.send_emoji`

Sends one predefined emoji reaction.

Payload:

| Field | Type | Required | Values |
|---|---|---:|---|
| `emoji_id` | string | yes | `thumbs_up`, `on_my_way`, `danger`, `nice`, `help` |

Payload must not include user-provided text. Server may rate-limit this command.

### `combat.send_quick_phrase`

Sends one predefined quick phrase.

Payload:

| Field | Type | Required | Values |
|---|---|---:|---|
| `phrase_id` | string | yes | `need_heal`, `shield_me`, `focus_marked`, `cooldown_ready`, `good_job`, `retreat` |

Payload must not include user-provided text. Localization/display copy belongs to frontend/server catalogs.

## 6. Server snapshots

### `lobby.snapshot`

Full lobby state sent after lobby join/reconnect and whenever server chooses to resync a client.

Minimum payload:

| Field | Type | Required |
|---|---|---:|
| `lobby_id` | string | yes |
| `raid_id` | string | yes |
| `phase` | string | yes: `waiting`, `countdown`, `locked`, `starting`, `started`, `cancelled` |
| `players` | array | yes |
| `players[].player_id` | string | yes |
| `players[].role_id` | string | yes |
| `players[].status` | string | yes |
| `players[].is_raid_lead` | boolean | yes |
| `party_recommendations` | array | yes, may be empty |
| `weekly_event` | object/null | yes |

### `battle.snapshot`

Full battle state sent after battle join/reconnect and at battle start.

Minimum payload:

| Field | Type | Required |
|---|---|---:|
| `battle_id` | string | yes |
| `lobby_id` | string | yes |
| `phase` | string | yes: `starting`, `active`, `resolving`, `completed`, `failed`, `abandoned` |
| `party_order` | array of entity ids | yes |
| `raid_lead_player_id` | string | yes |
| `entities` | array | yes |
| `entities[].entity_id` | string | yes |
| `entities[].kind` | string | yes: `player`, `enemy`, `boss` |
| `entities[].hp` | object/null | yes |
| `entities[].states` | array | yes |
| `entities[].effects` | array | yes |
| `entities[].skill_state` | array | for player entities |
| `entities[].target_hints` | array | for targetable entities |
| `links` | array | yes, may be empty |
| `last_raid_lead_command` | object/null | yes |
| `result` | object/null | yes |

Enemy ids, boss ids, state names and synergy primitives should align with `enemy_roster_v1.md`.

## 7. Server events

### `lobby.event`

Allowed `event_type` values:

```text
player_joined
player_left
player_status_changed
raid_lead_changed
raid_selected
countdown_started
countdown_cancelled
battle_created
lobby_locked
```

### `battle.event`

Allowed `event_type` values:

```text
skill_resolved
skill_rejected
hp_changed
effect_applied
effect_removed
entity_state_changed
enemy_state_changed
target_marked
link_changed
raid_lead_command_sent
emoji_sent
quick_phrase_sent
phase_changed
battle_completed
battle_failed
weekly_contribution_previewed
```

Communication events carry ids only: `command_id`, `emoji_id` or `phrase_id`. They must not carry arbitrary text
entered by a player.

## 8. Result and error flow

### `command.result`

Acknowledges accepted or duplicate commands. It does not replace battle/lobby events for actual state changes.

Payload:

| Field | Type | Required | Values / notes |
|---|---|---:|---|
| `status` | string | yes | `accepted`, `duplicate` |
| `command_type` | string | yes | Original command `type`. |
| `applied_server_seq` | number/null | yes | Sequence of related state event, if any. |
| `original_server_seq` | number/null | yes | For duplicates, sequence of the first result/error. |

### `command.error`

Rejects a command in a structured way. The client displays user-safe copy based on `code`, not raw server text.

Payload:

| Field | Type | Required | Notes |
|---|---|---:|---|
| `command_type` | string | yes | Original command `type`. |
| `code` | string | yes | One of the codes below. |
| `reason` | string | yes | Debug/logging text; not player-facing copy. |
| `retryable` | boolean | yes | Whether client may retry with same `client_command_id`. |
| `original_server_seq` | number/null | yes | For duplicate rejection, sequence of the first error. |

Allowed `code` values:

| Code | Meaning | Retryable |
|---|---|---:|
| `UNAUTHORIZED` | Session cannot control this player/entity. | no |
| `ROOM_NOT_FOUND` | Lobby/battle room is gone or unavailable. | no |
| `UNSUPPORTED_PROTOCOL` | `protocol` or `type` is not supported. | no |
| `INVALID_PAYLOAD` | Payload shape is invalid. | no |
| `INVALID_STATE` | Command is not valid in current lobby/battle phase. | no |
| `INVALID_TARGET` | Target does not satisfy skill/command rules. | no |
| `COOLDOWN_ACTIVE` | Skill exists but is not ready. | no |
| `NOT_RAID_LEAD` | Player cannot send raid lead command. | no |
| `RATE_LIMITED` | Emoji/quick phrase/command spam protection. | yes |
| `IDEMPOTENCY_CONFLICT` | Same `client_command_id`, different semantic payload. | no |
| `SERVER_BUSY` | Temporary server pressure. | yes |

## 9. PRD coverage

| PRD requirement | Protocol support |
|---|---|
| Live party/lobby state updates without manual refresh | `lobby.snapshot`, `lobby.event`, `lobby.set_player_status`. |
| Backend validates action and calculates result | `combat.use_skill` is intent-only; outcome arrives from server events. |
| UI shows skill result, cooldown/state and HP/effects | `battle.event` plus `battle.snapshot.entities[].skill_state/hp/effects`. |
| Live combat updates through WebSocket server push | `battle.snapshot`, `battle.event`. |
| No free text chat in combat | Only `command_id`, `emoji_id`, `phrase_id`; no text field accepted. |
| Raid lead predefined commands | `combat.send_raid_lead_command`. |
| Emoji and quick phrases | `combat.send_emoji`, `combat.send_quick_phrase`. |
| RL command with target highlights | `raid_lead_command_sent` with target refs; renderer highlights target. |

## 10. Downstream contract checklist

Backend tasks can reference these stable message names:

- Client commands: `lobby.set_player_status`, `combat.use_skill`, `combat.send_raid_lead_command`,
  `combat.send_emoji`, `combat.send_quick_phrase`.
- Server snapshots: `lobby.snapshot`, `battle.snapshot`.
- Server events: `lobby.event`, `battle.event`.
- Command acknowledgements: `command.result`, `command.error`.

Frontend tasks can rely on:

- fresh snapshot after join/reconnect;
- monotonic `server_seq` per room;
- no delta replay in v1;
- structured command errors for invalid target/cooldown/state;
- no free-form combat chat payloads;
- stable ids from ADR-0007, enemy roster and weekly event docs.
