# Technical documentation

Этот каталог хранит технические контракты Pocket Raid Tavern, которые нужны backend/frontend задачам до появления
исполняемой реализации.

## Документы

| Файл | Назначение |
|---|---|
| [docker-dev.md](docker-dev.md) | Docker-first локальный stack: `docker compose` (Postgres, backend, frontend), порты, health/OpenAPI/frontend smoke, pytest и `pnpm typecheck` через контейнеры. |
| [db-migrations.md](db-migrations.md) | Postgres + `DATABASE_URL`, политика Alembic (baseline только после human approval), команда `alembic upgrade head` на чистую БД через Compose. |
| [websocket-protocol-v1.md](websocket-protocol-v1.md) | Минимальный WebSocket protocol contract для lobby/combat v1: snapshots, events, commands, errors, sequence/idempotency и reconnect. |

## Правило обновления

- Если меняется состав сервисов Compose, порты или переменные окружения стека, обновлять [docker-dev.md](docker-dev.md) и при необходимости `.env.development.example` / `.env.production.example` / корневой `.env.example` в том же PR. Если меняется только процесс миграций или политика Alembic — [db-migrations.md](db-migrations.md).
- Если меняется WebSocket message name, payload shape или reconnect/idempotency behavior, обновлять protocol doc в том
  же PR, где меняется соответствующее решение.
- Если изменение расширяет scope v1 или меняет transport model, сначала оформить Linear issue и при необходимости ADR.
