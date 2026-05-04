# Docker Compose — локальный dev stack

## Docker-first workflow

Локальный dev **не требует** установки на хост **Node.js**, **Python**, **pnpm**, **uv** или **Postgres** — только **Docker** (и Git для клонирования репозитория). Все команды ниже, которые относятся к сервисам репозитория, рассчитаны на **один и тот же** env-файл: `docker compose --env-file .env.development <команда>`.

Короткий вход с проверками — в [корневом README](../../README.md). Индекс прочих техдоков без дублирования архитектуры — [README в этом каталоге](README.md) (например [db-migrations.md](db-migrations.md) для Alembic).

## Строгая проверка в Docker

Для агентов и разработчиков: изменения сервисов из этого Compose **обязаны** подтверждаться прогоном через Docker (сборка образа + smoke по сервису), а не только хостовыми `pnpm`/`uv`. Политика зафиксирована в [`.ai/rules/40-code-quality.md`](../../.ai/rules/40-code-quality.md) («Строгая проверка в Docker»).

**Файл `.env.development`:** не коммитится; шаблон — [`.env.development.example`](../../.env.development.example). Если файла нет — скопируй пример: `cp .env.development.example .env.development` (Windows: `Copy-Item .env.development.example .env.development`). Затем проверь валидность: `docker compose --env-file .env.development config` (должен завершиться с кодом 0). Секреты и что нельзя класть в git — в [`.ai/rules/80-security-and-secrets.md`](../../.ai/rules/80-security-and-secrets.md); оглавление env-шаблонов — [`.env.example`](../../.env.example).

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

5. Проверка OpenAPI: интерактивно **Swagger UI** — `http://localhost:18080/docs` (тот же хост-порт, что и у backend). Сырая схема: `http://localhost:18080/openapi.json`. Пример с `curl` (замени порт при отличии от дефолта):

```bash
curl -fsS "http://localhost:18080/openapi.json" | head -c 200
```

6. Проверка frontend: открой `http://localhost:15173` (порт см. `FRONTEND_PUBLISH_PORT`, по умолчанию **15173**). Должна открыться страница Vite с заголовком приложения.

## Качество кода через Docker (тесты / typecheck)

Предпочтительный путь для агентов и «чистой» машины — **только контейнеры** (тот же `.env.development`).

| Задача | Команда из корня репозитория |
|--------|------------------------------|
| Backend: pytest | `docker compose --env-file .env.development run --rm --no-deps backend uv run pytest -q` |
| Frontend: TypeScript (`tsc --noEmit`) | `docker compose --env-file .env.development run --rm --no-deps frontend pnpm run typecheck` |
| Frontend: Vitest (unit) | `docker compose --env-file .env.development run --rm --no-deps frontend pnpm run test:unit` |
| Frontend: Playwright (e2e) | Однократно установить браузер в образе: `docker compose --env-file .env.development run --rm --no-deps frontend pnpm exec playwright install chromium`, затем `docker compose --env-file .env.development run --rm --no-deps frontend pnpm run test:e2e` |

Отдельные **ESLint / Prettier (frontend)** и **Ruff / Black (backend)** в минимальном скелете не подключены: при появлении скриптов в `package.json` / `pyproject.toml` их следует вызывать так же через `docker compose run --rm --no-deps <сервис> …`.

**Опционально на хосте** (например, в CI или у разработчика с локальным `uv` / `pnpm`): зайти в `apps/backend` и выполнить `uv sync --frozen --group dev && uv run pytest -q`, в `apps/frontend` — `pnpm run typecheck`. Для согласованности с образами используй те же lockfile’ы (`uv.lock`, `pnpm-lock.yaml`).

## Pytest (backend smoke)

Образ `backend` собирается с **uv** и lockfile (`apps/backend/uv.lock`); dev-группа установлена в образе, чтобы можно было гонять тесты без отдельного Dockerfile.

Предпочтительно через Compose (см. таблицу выше):

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

Проверка TypeScript из контейнера — в разделе [«Качество кода через Docker»](#качество-кода-через-docker-тесты--typecheck).

Локальные E2E (Playwright) в `apps/frontend/playwright.config.ts` поднимают Vite на **отдельном порту 5174**, чтобы тесты не цеплялись к «чужому» dev server на `5173` и не мешали обычной разработке на дефолтном порту Compose.

### PWA Manifest (M3) manual checklist

Для задачи `PTR-23` (manifest baseline + prototype icon) ручная проверка выполняется после запуска frontend (`docker compose --env-file .env.development up frontend` или локально `pnpm run dev`):

1. Открыть `http://localhost:15173` (или свой `FRONTEND_PUBLISH_PORT`) и убедиться, что `GET /manifest.webmanifest` отдаёт JSON 200.
2. В DevTools открыть **Application → Manifest** и проверить:
   - `Name`: `Pocket Raid Tavern`
   - `Short name`: `PRT`
   - `Start URL`: `/`
   - `Theme color`: `#4f46e5`
   - `Background color`: `#f1f5f9`
3. Проверить, что иконка берётся из prototype-пути `icons/prototype/pwa-icon.svg`.
4. Проверить, что source notes присутствуют в `apps/frontend/public/icons/prototype/SOURCE_NOTES.md`.
5. Подтвердить, что в задаче **нет** service worker и offline gameplay queue (вне scope `PTR-23`).

### Smoke (build + up + curl)

Требуется файл **`.env.development`** в корне (скопируй из `.env.development.example`):

```bash
bash scripts/smoke-frontend-docker.sh
```

