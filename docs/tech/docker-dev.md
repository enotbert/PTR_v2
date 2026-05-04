# Docker Compose — локальный dev stack

## Строгая проверка в Docker

Для агентов и разработчиков: изменения сервисов из этого Compose **обязаны** подтверждаться прогоном через Docker (сборка образа + smoke по сервису), а не только хостовыми `pnpm`/`uv`. Политика зафиксирована в [`.ai/rules/40-code-quality.md`](../../.ai/rules/40-code-quality.md) («Строгая проверка в Docker»).

**Файл `.env.development`:** не коммитится; шаблон — [`.env.development.example`](../../.env.development.example). Если файла нет — скопируй пример: `cp .env.development.example .env.development` (Windows: аналог). Затем проверь валидность: `docker compose --env-file .env.development config` (должен завершиться с кодом 0).

---

Минимальный состав (PTR-17 / PTR-19): **`postgres`**, **`backend`** (FastAPI), **`frontend`** (Vite dev server + React + TypeScript).

Файлы: корневой `docker-compose.yml`, контексты `apps/backend/` и `apps/frontend/`.

## Порты (публикация на хост)

Дефолты **намеренно нестандартные**, чтобы не пересекаться с типичными локальными сервисами: Postgres **5432**, HTTP **8000**, Vite **5173**. Внутри Docker-сети сервисы по-прежнему слушают стандартные контейнерные порты (см. `docker-compose.yml`).

| Сервис    | Контейнер | Переменная хост-порта   | По умолчанию (хост → контейнер) |
|-----------|-----------|-------------------------|----------------------------------|
| Postgres  | `postgres` | `POSTGRES_PUBLISH_PORT` | `15432 → 5432`                   |
| Backend   | `backend` | `BACKEND_PUBLISH_PORT`  | `18080 → 8000`                   |
| Frontend  | `frontend`| `FRONTEND_PUBLISH_PORT` | `15173 → 5173`                   |

При коллизии с другими процессами задай другие значения в [.env.development.example](../../.env.development.example) (после копирования в `.env.development`) или переопредели переменные в своём env-файле.

## Быстрый старт

1. Скопируй [.env.development.example](../../.env.development.example) в **`.env.development`** в корне (файл в `.gitignore`, не коммитить). Для продакшен-окружения используй отдельный шаблон [.env.production.example](../../.env.production.example) и инжект секретов через платформу — **не** переиспользуй dev-пароли.
2. Собери конфигурацию Compose (быстрая проверка синтаксиса):

```bash
docker compose --env-file .env.development config
```

3. Подними стек:

```bash
docker compose --env-file .env.development up --build
```

4. Проверка backend и Postgres: открой `http://localhost:18080/health` (порт см. `BACKEND_PUBLISH_PORT`, по умолчанию **18080**). Ожидается JSON с `"postgres": "reachable"` после того, как сервис `postgres` станет healthy.

5. Проверка frontend: открой `http://localhost:15173` (порт см. `FRONTEND_PUBLISH_PORT`, по умолчанию **15173**). Должна открыться страница Vite с заголовком приложения.

## Pytest (backend smoke)

Образ `backend` собирается с **uv** и lockfile (`apps/backend/uv.lock`); dev-группа установлена в образе, чтобы можно было гонять тесты без отдельного Dockerfile.

Локально (из корня репозитория):

```bash
cd apps/backend
uv sync --frozen --group dev
uv run pytest -q
```

Внутри Compose после `docker compose ... build` (тот же `--env-file`, что и для `up`):

```bash
docker compose --env-file .env.development run --rm --no-deps backend uv run pytest -q
```

Команда `run --no-deps` поднимает одноразовый контейнер с тем же образом, что и у сервиса `backend`, без старта `postgres`; для этих smoke-тестов БД мокируется в pytest.

## Сеть и подключение к БД

Сервисы разделяют **дефолтную сеть Compose**. Backend получает строку **`DATABASE_URL`** (см. `docker-compose.yml`) с хостом `postgres` и портом `5432` внутри сети. Менять хост при локальном compose не требуется.

## Миграции БД (Alembic)

Конфиг Alembic и ревизии лежат в **`apps/backend/`** (`alembic.ini`, каталог `alembic/`). Команды `upgrade head` / `current` и политика для агентов — в **[db-migrations.md](db-migrations.md)**.

## Frontend (Vite dev)

Сервис **`frontend`** собирается из `apps/frontend/` (**pnpm** + Vite 6 + React + TypeScript). Внутри контейнера dev server слушает **`0.0.0.0:5173`**; на хост публикуется `FRONTEND_PUBLISH_PORT` → `5173`.

### API origin (`VITE_API_BASE_URL`)

Браузер пользователя обращается к backend по **хостовому** URL (не по имени сервиса `backend` внутри Docker-сети). В `docker-compose.yml` для `frontend` задано:

`VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:18080}`

То есть по умолчанию используется тот же хост, что и у дефолтного `BACKEND_PUBLISH_PORT` (**18080**). Переопредели переменную в `.env.development` при других портах или reverse proxy. **Не клади продакшен-секреты** в репозиторий — только примеры в `.env.development.example`.

### Bind mount и `node_modules`

Для HMR исходники монтируются как `./apps/frontend:/app`, а **`node_modules`** держится в именованном volume `frontend_node_modules`, чтобы не затирать установленные в образе зависимости содержимым с хоста.

### TypeScript check через Docker

Из корня репозитория:

```bash
docker compose --env-file .env.development run --rm --no-deps frontend pnpm run typecheck
```

### Smoke (build + up + curl)

Требуется файл **`.env.development`** в корне (скопируй из `.env.development.example`):

```bash
bash scripts/smoke-frontend-docker.sh
```

