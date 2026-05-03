# PTR v2

Monorepo Pocket Raid Tavern. Процесс и роли AI-разработчиков: [AGENTS.md](AGENTS.md).

## Локальный dev stack (Docker)

Узел входа описан в [docs/tech/docker-dev.md](docs/tech/docker-dev.md). Кратко:

```bash
cp .env.development.example .env.development
docker compose --env-file .env.development config
docker compose --env-file .env.development up --build
```

Шаблоны окружений: [.env.development.example](.env.development.example) (локально + Compose), [.env.production.example](.env.production.example) (прод: только имена переменных, секреты с платформы). Оглавление — [.env.example](.env.example).
