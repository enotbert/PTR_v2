# Миграции БД (Alembic) — локальный dev workflow

Документ описывает, как в репозитории устроены **Postgres** и **применение миграций** в локальном стеке Docker. Источник правды по compose, порту и health — [docker-dev.md](docker-dev.md).

## Текущее состояние (PTR-20)

- Сервис **`postgres`** в корневом `docker-compose.yml`: образ, volume данных, **`healthcheck`** (`pg_isready`), публикация порта на хост.
- Сервис **`backend`** получает **`DATABASE_URL`** (строка подключения к хосту `postgres` и порту `5432` внутри сети Compose). Значение собирается из переменных `POSTGRES_*` в compose; см. тот же файл.
- Проверка подключения из приложения: HTTP **`GET /health`** — при успешном `SELECT 1` возвращается `"postgres": "reachable"` (см. `apps/backend/app/main.py`).

## Политика: baseline и файлы Alembic

Добавление **revision-файлов Alembic**, правок существующих миграций и изменение **схемы БД в коде** без явного согласования с человеком — в чёрном списке для агентов; см. [`.ai/rules/90-forbidden.md`](../../.ai/rules/90-forbidden.md) и критерии задачи **PTR-20** в Linear.

Пока **нет** human approval на initial schema:

- в репозитории **не** хранятся `alembic.ini`, каталог `alembic/`, `versions/*.py`;
- ниже — **целевой** workflow после того, как отдельным решением/PR будут добавлены Alembic и baseline.

## Команда применения миграций на чистую БД (после появления Alembic)

Предпосылки: в корне есть `.env.development` (копия [`.env.development.example`](../../.env.development.example)), образы собраны (`docker compose ... build` при необходимости), в дереве уже лежат конфиг Alembic и ревизии (отдельный PR после approval).

1. Поднять только Postgres и дождаться healthy (или поднять весь стек — главное, чтобы `postgres` был healthy):

```bash
docker compose --env-file .env.development up -d postgres
```

2. Одноразовый контейнер backend в той же сети Compose, с тем же `DATABASE_URL`, что у сервиса `backend`:

```bash
docker compose --env-file .env.development run --rm backend uv run alembic upgrade head
```

**Не** использовать `run --no-deps` для этой команды: контейнеру нужна сеть Compose и резолв хоста `postgres`.

На **пустой** БД команда применяет все ревизии до `head`. Повторный запуск идемпотентен для уже применённых версий.

## Запуск миграций при уже поднятом стеке

Если `docker compose ... up` уже выполнен и `postgres` healthy:

```bash
docker compose --env-file .env.development run --rm backend uv run alembic upgrade head
```

## Backend на хосте (вне Docker)

Если `uvicorn` запускается на машине разработчика, задайте **`DATABASE_URL`** на опубликованный порт Postgres (по умолчанию хост `127.0.0.1`, порт **15432** — см. `POSTGRES_PUBLISH_PORT` в примере env и [docker-dev.md](docker-dev.md)). Пример см. в [`.env.development.example`](../../.env.development.example).

## Внешние и production окружения

Не запускать миграции из этого документа на внешних/production БД без отдельного runbook и секретов платформы. Dev-пароли в примерах — только для локального compose.

## Связанные правила и задачи

- Строгая проверка compose: [`.ai/rules/40-code-quality.md`](../../.ai/rules/40-code-quality.md), раздел про Docker в [docker-dev.md](docker-dev.md).
- Закрытие PTR-20 не требует коммита файлов Alembic до explicit human approval на baseline.
