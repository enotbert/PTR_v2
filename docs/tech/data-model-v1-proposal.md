# Initial data model v1 (proposal)

Статус: proposed (ожидает human approval по границам initial migrations).

Связано с: `PTR-27`, [PRD v1](../product/PRD_v1_public_early_access.md), [websocket-protocol-v1](websocket-protocol-v1.md), [db-migrations](db-migrations.md).

## 1. Цель и границы

Документ фиксирует минимальную реляционную модель для v1 core loop:

- player/session;
- tavern и вклад;
- party/raid lifecycle;
- combat events (server-authoritative);
- rewards и идемпотентная выдача;
- invite/share;
- базовая аналитика.

Вне scope этого документа:

- конкретные Alembic revision-файлы;
- production implementation;
- финальные индексы под high-load (кроме базового набора для v1).

## 2. Backend authority boundary

Postgres хранит only-source-of-truth для:

- identity и membership (`players`, `sessions`, `party_members`);
- raid/battle lifecycle (`raids`, `battles`, `battle_participants`);
- authoritative outcome (`battle_events`, `reward_claims`, `tavern_contributions`);
- anti-duplicate guarantees (`command_dedup`, `reward_claims.idempotency_key`);
- business-level invite/share links (`invites`).

Computed/derived state (может пересчитываться):

- read models для UI (например, агрегаты таверны и lobby snapshots);
- денормализованные leaderboard/analytics views;
- краткоживущий realtime cache поверх WebSocket rooms.

## 3. Entity model (v1)

### 3.1 Identity and session

- `players`
  - `id` (PK, ULID/UUID)
  - `display_name`
  - `created_at`, `updated_at`
  - `last_seen_at`
  - `is_active`
- `sessions`
  - `id` (PK)
  - `player_id` (FK -> `players.id`)
  - `device_fingerprint` (nullable)
  - `issued_at`, `expires_at`, `revoked_at`
  - `last_ip`, `last_user_agent` (nullable)

### 3.2 Tavern and progression

- `taverns`
  - `id` (PK)
  - `slug` (UNIQUE)
  - `name`
  - `tier`
  - `created_at`, `updated_at`
- `player_tavern_state`
  - `id` (PK)
  - `player_id` (FK -> `players.id`)
  - `tavern_id` (FK -> `taverns.id`)
  - `reputation`
  - `weekly_points`
  - `updated_at`
  - UNIQUE (`player_id`, `tavern_id`)
- `tavern_contributions`
  - `id` (PK)
  - `player_id` (FK -> `players.id`)
  - `tavern_id` (FK -> `taverns.id`)
  - `source_type` (`raid_reward`, `weekly_event`, `manual_spend`)
  - `source_ref` (raid id / event id)
  - `amount`
  - `created_at`

### 3.3 Party, raid, battle

- `parties`
  - `id` (PK)
  - `tavern_id` (FK -> `taverns.id`)
  - `created_by_player_id` (FK -> `players.id`)
  - `status` (`open`, `locked`, `in_raid`, `archived`)
  - `created_at`, `updated_at`
- `party_members`
  - `id` (PK)
  - `party_id` (FK -> `parties.id`)
  - `player_id` (FK -> `players.id`)
  - `role_id` (string, contract id from skill set)
  - `is_raid_lead`
  - `joined_at`, `left_at` (nullable)
  - UNIQUE (`party_id`, `player_id`)
- `raids`
  - `id` (PK)
  - `party_id` (FK -> `parties.id`)
  - `raid_template_id` (string)
  - `status` (`pending`, `active`, `completed`, `failed`, `abandoned`)
  - `started_at`, `ended_at` (nullable)
- `battles`
  - `id` (PK)
  - `raid_id` (FK -> `raids.id`, UNIQUE)
  - `phase` (`starting`, `active`, `resolving`, `completed`, `failed`, `abandoned`)
  - `server_seq` (bigint, monotonic per battle)
  - `created_at`, `updated_at`
- `battle_participants`
  - `id` (PK)
  - `battle_id` (FK -> `battles.id`)
  - `entity_id` (string, stable in protocol scope)
  - `entity_kind` (`player`, `enemy`, `boss`)
  - `player_id` (nullable FK -> `players.id`, only for `entity_kind=player`)
  - `slot_order` (int)
  - UNIQUE (`battle_id`, `entity_id`)

### 3.4 Combat events and idempotency

- `battle_events`
  - `id` (PK, technical key)
  - `battle_id` (FK -> `battles.id`)
  - `server_seq` (bigint)
  - `event_type` (matches protocol)
  - `payload_json` (jsonb)
  - `occurred_at`
  - UNIQUE (`battle_id`, `server_seq`)
  - Physical layout: partitioned by `battle_id` (hash/list strategy), so each battle stream is isolated in its own partition group
  - Partition key invariant: every query path to events must include `battle_id`
  - Minimal indexes per partition:
    - (`battle_id`, `server_seq`) UNIQUE
    - (`battle_id`, `occurred_at`)
- `command_dedup`
  - `id` (PK)
  - `player_id` (FK -> `players.id`)
  - `room_kind` (`lobby`, `battle`)
  - `room_id` (string)
  - `client_command_id` (string)
  - `command_type` (string)
  - `payload_hash` (string)
  - `result_kind` (`accepted`, `rejected`)
  - `original_server_seq` (nullable bigint)
  - `created_at`, `expires_at`
  - UNIQUE (`player_id`, `room_kind`, `room_id`, `client_command_id`)

### 3.5 Rewards and claims

- `rewards`
  - `id` (PK)
  - `player_id` (FK -> `players.id`)
  - `raid_id` (nullable FK -> `raids.id`)
  - `reward_type` (`loot`, `weekly`, `invite_bonus`)
  - `payload_json` (jsonb)
  - `created_at`
- `reward_claims`
  - `id` (PK)
  - `reward_id` (FK -> `rewards.id`)
  - `player_id` (FK -> `players.id`)
  - `idempotency_key` (string)
  - `claimed_at`
  - UNIQUE (`reward_id`, `player_id`)
  - UNIQUE (`player_id`, `idempotency_key`)

### 3.6 Invite/share and analytics

- `invites`
  - `id` (PK)
  - `created_by_player_id` (FK -> `players.id`)
  - `raid_id` (nullable FK -> `raids.id`)
  - `token` (UNIQUE)
  - `status` (`active`, `used`, `expired`, `revoked`)
  - `created_at`, `expires_at`, `used_at` (nullable)
- `analytics_events`
  - `id` (PK)
  - `event_name` (string)
  - `player_id` (nullable FK -> `players.id`)
  - `session_id` (nullable FK -> `sessions.id`)
  - `raid_id` (nullable FK -> `raids.id`)
  - `battle_id` (nullable FK -> `battles.id`)
  - `event_at`
  - `payload_json` (jsonb)

## 4. Initial migration scope (для human approval)

Рекомендуемый initial scope (v1 baseline):

1. Identity/session: `players`, `sessions`.
2. Tavern/progress: `taverns`, `player_tavern_state`, `tavern_contributions`.
3. Party/raid/battle: `parties`, `party_members`, `raids`, `battles`, `battle_participants`.
4. Authority/event/idempotency: `battle_events` (partitioned by `battle_id`), `command_dedup`.
5. Reward/invite: `rewards`, `reward_claims`, `invites`.
6. Product analytics minimum: `analytics_events`.

Out of initial migration scope:

- materialized views/read models;
- long-term retention automation.

## 5. Flow coverage against PRD

- First session: `players`, `sessions`, `raids`, `rewards`, `reward_claims`, `player_tavern_state`.
- Regular raid: `parties`, `party_members`, `raids`, `battles`, `battle_events`, `command_dedup`.
- Social/share: `invites`, invite-linked `raids`, optional `invite_bonus` in `rewards`.
- Weekly/progress visibility: `tavern_contributions`, `player_tavern_state`, `analytics_events`.

## 6. Backend authority checklist

- [x] Все authoritative outcomes фиксируются сервером (`battle_events`, `reward_claims`, `tavern_contributions`).
- [x] Для realtime-команд есть dedup ключ (`command_dedup` по player/room/client_command_id).
- [x] Для reward claim есть идемпотентность (`player_id + idempotency_key`).
- [x] Клиент не может стать source of truth для battle/reward outcome.
- [x] Есть явная граница между persisted state и computed/read-model state.

## 7. Risks and follow-ups

## 7. Retention policy for analytics events (v1)

Цель: контролировать рост `analytics_events` без потери продуктовых сигналов для PRD funnel.

Политика хранения:

- Hot window (raw): 30 дней в `analytics_events` без агрегации потерь.
- Warm window (aggregated): 180 дней в суточных агрегатах (`event_name`, `event_date`, `platform`, `build_channel`).
- Cold window: старше 180 дней raw-данные удаляются после успешной агрегации и smoke-проверки метрик.

Операционный цикл:

1. Ежедневный job строит/обновляет агрегаты за D-1.
2. Валидация: сравнение raw vs aggregate totals с допустимым отклонением 0%.
3. Удаление raw старше 30 дней пачками (по `event_at`) с лимитом на транзакцию.
4. Еженедельный контрольный отчёт по объёму таблицы и top event families.

Минимальные guardrails:

- DELETE только по диапазону `event_at` и в off-peak окно.
- Отдельный kill-switch для retention job.
- Метрики job: duration, deleted_rows, lag_days, validation_failed.
- При `validation_failed > 0` удаление блокируется до ручного разбора.

## 8. Risks and follow-ups

1. `battle_events` partition-by-`battle_id` увеличивает DDL/операционную сложность; нужен runbook ротации partition groups.
2. `analytics_events` retention зависит от стабильного daily aggregation pipeline; его падение ведёт к накоплению raw.
3. `role_id`, `raid_template_id`, `event_type` пока строковые контракты; может понадобиться reference catalog таблиц.
4. Для social features вероятно потребуется отдельная таблица invite impressions/attribution.

Рекомендуемые follow-up задачи:

- ADR/issue на runbook и автоматику partition management для `battle_events`.
- ADR/issue на реализацию retention job + aggregate store для `analytics_events`.
- ADR/issue на catalog strategy (roles, raid templates, enemy ids) vs hardcoded contracts.
- Issue на read-model projections для tavern/home screen latency.
