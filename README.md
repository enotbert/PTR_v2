# PTR v2

Monorepo Pocket Raid Tavern. Процесс и роли AI-разработчиков: [AGENTS.md](AGENTS.md).

## Локальный dev stack (Docker)

Узел входа описан в [docs/tech/docker-dev.md](docs/tech/docker-dev.md). Кратко:

```bash
docker compose config
docker compose up --build
```

Переменные окружения для Compose — см. [.env.example](.env.example) (демо-имена и комментарии, без секретов).
