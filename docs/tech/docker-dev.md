# Docker Compose — локальный dev stack

Минимальный состав (PTR-17): **`postgres`**, **`backend`** (FastAPI), **`frontend`** (заготовка порта до появления Vite bundle).

Файлы: корневой `docker-compose.yml`, контексты `apps/backend/` и `apps/frontend/`.

## Порты (публикация на хост)

Дефолты **намеренно нестандартные**, чтобы не пересекаться с типичными локальными сервисами: Postgres **5432**, HTTP **8000**, Vite **5173**. Внутри Docker-сети сервисы по-прежнему слушают стандартные контейнерные порты (см. `docker-compose.yml`).

| Сервис    | Контейнер | Переменная хост-порта   | По умолчанию (хост → контейнер) |
|-----------|-----------|-------------------------|----------------------------------|
| Postgres  | `postgres` | `POSTGRES_PUBLISH_PORT` | `15432 → 5432`                   |
| Backend   | `backend` | `BACKEND_PUBLISH_PORT`  | `18080 → 8000`                   |
| Frontend  | `frontend`| `FRONTEND_PUBLISH_PORT` | `15173 → 5173`                   |

При коллизии с другими процессами задай другие значения в `.env` (имена см. [.env.example](../../.env.example)).

## Быстрый старт

1. Создай файл `.env` в корне (не коммитить). Ориентир по именам переменных — `.env.example`.
2. Собери конфигурацию Compose (быстрая проверка синтаксиса):

```bash
docker compose config
```

3. Подними стек:

```bash
docker compose up --build
```

4. Проверка backend и Postgres: открой `http://localhost:18080/health` (порт см. `BACKEND_PUBLISH_PORT`, по умолчанию **18080**). Ожидается JSON с `"postgres": "reachable"` после того, как сервис `postgres` станет healthy.

## Сеть и подключение к БД

Сервисы разделяют **дефолтную сеть Compose**. Backend получает строку **`DATABASE_URL`** (см. `docker-compose.yml`) с хостом `postgres` и портом `5432` внутри сети. Менять хост при локальном compose не требуется.

## Frontend

Образ только резервирует порт **`5173`** и держит контейнер активным до появления манифестов пакетного менеджера приложения (`package.json` / lockfile и т.д.). Тогда нужно будет заменить `CMD` в `apps/frontend/Dockerfile` на реальный dev/production entrypoint.

