# Docker Compose — локальный dev stack

Минимальный состав (PTR-17): **`postgres`**, **`backend`** (FastAPI), **`frontend`** (заготовка порта до появления Vite bundle).

Файлы: корневой `docker-compose.yml`, контексты `apps/backend/` и `apps/frontend/`.

## Порты (публикация на хост)

| Сервис    | Контейнер | Переменная хост-порта   | По умолчанию |
|-----------|-----------|-------------------------|--------------|
| Postgres  | `postgres` | `POSTGRES_PUBLISH_PORT` | `5432`       |
| Backend   | `backend` | `BACKEND_PUBLISH_PORT`  | `8000`       |
| Frontend  | `frontend`| `FRONTEND_PUBLISH_PORT` | `5173`       |

## Быстрый старт

Если локально уже заняты порты **5432** или **5173**, задай в `.env` свои `POSTGRES_PUBLISH_PORT` / `FRONTEND_PUBLISH_PORT` (см. `.env.example`).

1. Создай файл `.env` в корне (не коммитить). Ориентир по именам переменных — `.env.example`.
2. Собери конфигурацию Compose (быстрая проверка синтаксиса):

```bash
docker compose config
```

3. Подними стек:

```bash
docker compose up --build
```

4. Проверка backend и Postgres: открой `http://localhost:8000/health` (порт см. `BACKEND_PUBLISH_PORT`). Ожидается JSON с `"postgres": "reachable"` после того, как сервис `postgres` станет healthy.

## Сеть и подключение к БД

Сервисы разделяют **дефолтную сеть Compose**. Backend получает строку **`DATABASE_URL`** (см. `docker-compose.yml`) с хостом `postgres` и портом `5432` внутри сети. Менять хост при локальном compose не требуется.

## Frontend

Образ только резервирует порт **`5173`** и держит контейнер активным до появления манифестов пакетного менеджера приложения (`package.json` / lockfile и т.д.). Тогда нужно будет заменить `CMD` в `apps/frontend/Dockerfile` на реальный dev/production entrypoint.

