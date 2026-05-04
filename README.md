# PTR v2

Monorepo Pocket Raid Tavern. Процесс и роли AI-разработчиков: [AGENTS.md](AGENTS.md).

## Локальная разработка (Docker-first)

Поднятие **Postgres**, **backend** (FastAPI) и **frontend** (Vite) описано в одном месте: **[docs/tech/docker-dev.md](docs/tech/docker-dev.md)**. Здесь — минимальный вход без установки **Node.js**, **Python** или **Postgres на хосте**: нужны только **Git**, **Docker** и Docker Compose (v2, входит в Docker Desktop / Engine).

### Быстрый старт

1. Скопируй шаблон окружения в **`.env.development`** (файл в `.gitignore`, в репозиторий не коммитить):

   ```bash
   cp .env.development.example .env.development
   ```

   PowerShell: `Copy-Item .env.development.example .env.development`

2. Проверь, что Compose собирает конфигурацию без ошибок:

   ```bash
   docker compose --env-file .env.development config
   ```

3. Подними стек:

   ```bash
   docker compose --env-file .env.development up --build
   ```

### Smoke после старта

Подставь свои порты из `.env.development`, если менял дефолты из [.env.development.example](.env.development.example).

| Проверка | Куда смотреть |
|----------|----------------|
| Health и доступность Postgres | `http://localhost:18080/health` (`BACKEND_PUBLISH_PORT`, по умолчанию **18080**) — ожидается JSON с `"status": "ok"` и `"postgres": "reachable"`. |
| OpenAPI | Документация Swagger UI: `http://localhost:18080/docs`; схема JSON: `http://localhost:18080/openapi.json`. |
| Frontend (первая загрузка) | `http://localhost:15173` (`FRONTEND_PUBLISH_PORT`, по умолчанию **15173**). |

Команды **lint / typecheck / тесты** через контейнеры — в разделе «Качество кода через Docker» в [docs/tech/docker-dev.md](docs/tech/docker-dev.md).

### Переменные окружения и секреты

Оглавление шаблонов: [.env.example](.env.example). Локальная разработка: [.env.development.example](.env.development.example). Продакшен-имена переменных (без значений секретов): [.env.production.example](.env.production.example). Политика: [`.ai/rules/80-security-and-secrets.md`](.ai/rules/80-security-and-secrets.md) — **не коммитить** реальные секреты и не копировать dev-пароли в прод.

### Где искать архитектуру

Детали стека, миграций и контрактов без дублирования в README — индекс [docs/tech/README.md](docs/tech/README.md) (например [docker-dev.md](docs/tech/docker-dev.md), [db-migrations.md](docs/tech/db-migrations.md)).
