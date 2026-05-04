# Миграции БД (Alembic) — локальный dev workflow

Документ описывает, как в репозитории устроены **Postgres** и **применение миграций** в локальном стеке Docker. Источник правды по compose, порту и health — [docker-dev.md](docker-dev.md).

## Текущее состояние

- Сервис **`postgres`** в корневом `docker-compose.yml`: образ, volume данных, **`healthcheck`** (`pg_isready`), публикация порта на хост.
- Сервис **`backend`** получает **`DATABASE_URL`** (строка подключения к хосту `postgres` и порту `5432` внутри сети Compose). Значение собирается из переменных `POSTGRES_*` в compose; см. тот же файл.
- Проверка подключения из приложения: HTTP **`GET /health`** — при успешном `SELECT 1` возвращается `"postgres": "reachable"` (см. `apps/backend/app/main.py`).
- **Alembic** в каталоге `apps/backend/`: `alembic.ini`, пакет `alembic/` с `env.py` и ревизиями в `alembic/versions/`. URL для миграций берётся из **`DATABASE_URL`**; строка `postgresql://…` приводится к виду **`postgresql+psycopg://…`** для SQLAlchemy 2 + psycopg3.

## Политика для агентов

Добавление **новых** revision-файлов, правок **чужих** уже применённых миграций в проде и смена схемы без согласования с человеком — по-прежнему в чёрном списке; см. [`.ai/rules/90-forbidden.md`](../../.ai/rules/90-forbidden.md). Baseline после human approval на initial schema — в репозитории (см. Linear PTR-20 / PTR-66).

## Команда применения миграций на чистую БД

Предпосылки: в корне есть `.env.development` (копия [`.env.development.example`](../../.env.development.example)), образ `backend` собран (`docker compose ... build backend` при необходимости).

1. Поднять Postgres и дождаться healthy (или поднять весь стек — главное, чтобы `postgres` был healthy):

```bash
docker compose --env-file .env.development up -d postgres
```

2. Одноразовый контейнер backend в той же сети Compose, с тем же `DATABASE_URL`, что у сервиса `backend`:

```bash
docker compose --env-file .env.development run --rm backend uv run alembic upgrade head
```

**Не** использовать `run --no-deps` для этой команды: контейнеру нужна сеть Compose и резолв хоста `postgres`.

На **пустой** БД команда применяет все ревизии до `head`. Повторный запуск идемпотентен для уже применённых версий.

Проверить текущую ревизию:

```bash
docker compose --env-file .env.development run --rm backend uv run alembic current
```

## Запуск миграций при уже поднятом стеке

Если `docker compose ... up` уже выполнен и `postgres` healthy:

```bash
docker compose --env-file .env.development run --rm backend uv run alembic upgrade head
```

## Новая ревизия (разработчики)

Из каталога `apps/backend` при заданном `DATABASE_URL` (или через `docker compose run --rm backend sh -lc 'cd /app && uv run alembic revision -m "..."'`):

```bash
cd apps/backend
export DATABASE_URL=postgresql://…   # или хост + порт опубликованного Postgres
uv run alembic revision -m "describe_change"
```

Для автогенерации по моделям SQLAlchemy позже понадобится `target_metadata` в `alembic/env.py` — до этого править миграции вручную.

## Backend на хосте (вне Docker)

Если `uvicorn` или `alembic` запускаются на машине разработчика, задайте **`DATABASE_URL`** на опубликованный порт Postgres (по умолчанию хост `127.0.0.1`, порт **15432** — см. `POSTGRES_PUBLISH_PORT` в примере env и [docker-dev.md](docker-dev.md)). Пример см. в [`.env.development.example`](../../.env.development.example).

## Внешние и production окружения

Не запускать миграции из этого документа на внешних/production БД без отдельного runbook и секретов платформы. Dev-пароли в примерах — только для локального compose.

## Связанные правила

- Строгая проверка compose: [`.ai/rules/40-code-quality.md`](../../.ai/rules/40-code-quality.md), раздел про Docker в [docker-dev.md](docker-dev.md).
