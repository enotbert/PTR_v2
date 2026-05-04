# Frontend (Vite + React + TypeScript)

Dev server listens on **5173** inside the container; Compose publishes it as `FRONTEND_PUBLISH_PORT` (default **15173** on the host).

## Local (without Docker)

```bash
corepack enable
cd apps/frontend
pnpm install
pnpm run dev
```

Open `http://localhost:5173`. Set `VITE_API_BASE_URL` in a `.env` file next to `package.json` if needed.

## Docker Compose

From repo root (with `.env.development` — copy from `.env.development.example`):

```bash
docker compose --env-file .env.development up --build frontend
```

Then open `http://localhost:15173` (or your `FRONTEND_PUBLISH_PORT`). The app reads **`VITE_API_BASE_URL`** at dev-server time; defaults are set in `docker-compose.yml` and documented in `docs/tech/docker-dev.md`.

## Typecheck

```bash
docker compose --env-file .env.development run --rm --no-deps frontend pnpm run typecheck
```
