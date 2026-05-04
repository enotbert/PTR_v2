# PTR-19 — Frontend Vite dev server in Docker

## Goal

Реализовать минимальный **React + Vite + TypeScript** scaffold в `apps/frontend`, чтобы сервис `frontend` в корневом `docker-compose.yml` поднимал **реальный Vite dev server** (порт **5173** в контейнере, публикация на хост через `FRONTEND_PUBLISH_PORT`). Страница должна открываться в браузере с хоста. **API base URL** для браузера конфигурируется через **`VITE_API_BASE_URL`** (без прод-секретов; только dev-дефолты в доке и `.env.development.example`). Задокументировать команды **TypeScript check** и **smoke** через Docker.

См. Linear [PTR-19](https://linear.app/ptr-game/issue/PTR-19/podnyat-frontend-dev-server-v-docker). PTR-16 (approval manifests) — **Done**; добавление `package.json` / `pnpm-lock.yaml` в scope этой задачи **разрешено**.

## Context

- Сейчас `apps/frontend/Dockerfile` — placeholder (`tail -f /dev/null`), `README.md` краткий. Корневой `docker-compose.yml` уже объявляет сервис `frontend` с портом `15173:5173` и `depends_on: backend`.
- Стек по продуктовой линии: **pnpm** + React + Vite + TypeScript (согласовано в PTR-16 / ADR-0001 tech narrative в Linear; в репо нет отдельного tech-stack ADR — ориентир на описание задачи).
- Браузер пользователя ходит на backend по **хостовому** URL (например `http://localhost:18080`), не `http://backend:8000` — это важно для `import.meta.env.VITE_API_BASE_URL`.
- Оркестратор после твоего прогона может выполнить `pnpm install` локально, если lockfile потребует доработки; по возможности создай корректный **`pnpm-lock.yaml`** вместе с `package.json` (консистентные версии).

## Files in scope

Можно **создавать и изменять только** перечисленное:

| Path | Action |
|------|--------|
| `apps/frontend/package.json` | NEW — `pnpm`, scripts: `dev`, `build`, `typecheck` (или `tsc --noEmit`), зависимости: `react`, `react-dom`, `typescript`, `vite`, `@vitejs/plugin-react`, типы `@types/react`, `@types/react-dom` |
| `apps/frontend/pnpm-lock.yaml` | NEW — предпочтительно сгенерированный lock; если генерация недоступна из среды, оставь минимально валидный набор в `package.json` и опиши в `## Result` что lock добавит оркестратор |
| `apps/frontend/tsconfig.json` | NEW — strict TS, `jsx: react-jsx`, paths для Vite |
| `apps/frontend/tsconfig.node.json` | NEW — для `vite.config.ts` |
| `apps/frontend/vite.config.ts` | NEW — `plugin-react`, `server: { host: "0.0.0.0", port: 5173 }`, при необходимости `watch: { usePolling: true }` для Docker bind mounts |
| `apps/frontend/index.html` | NEW — entry `src/main.tsx` |
| `apps/frontend/src/main.tsx` | NEW |
| `apps/frontend/src/App.tsx` | NEW — минимальная главная: заголовок + отображение **текущего** `import.meta.env.VITE_API_BASE_URL` (как текст), без прод URL |
| `apps/frontend/src/index.css` | NEW — минимальные базовые стили (не обязательно CSS framework) |
| `apps/frontend/src/vite-env.d.ts` | NEW — `/// <reference types="vite/client" />` и тип для `VITE_API_BASE_URL` |
| `apps/frontend/.dockerignore` | NEW — `node_modules`, `dist`, `.git`, кеши |
| `apps/frontend/Dockerfile` | REPLACE — multi-stage не обязателен; **Node 22 bookworm slim**, `corepack enable` + **pnpm**, `WORKDIR /app`, copy manifests, `pnpm install --frozen-lockfile` (если lock есть; иначе `pnpm install`), copy исходники, `EXPOSE 5173`, `CMD` запускает **`pnpm run dev`** (Vite с `--host 0.0.0.0` либо через script в `package.json`) |
| `apps/frontend/README.md` | UPDATE — как собрать/запустить локально и через Compose |
| `docker-compose.yml` | UPDATE — для `frontend`: передать `environment` с `VITE_API_BASE_URL` из `${VITE_API_BASE_URL:-http://localhost:18080}` (дефолт согласован с `BACKEND_PUBLISH_PORT` **18080**); опционально `CHOKIDAR_USEPOLLING: "true"` для file watch в Docker; **bind mount** `./apps/frontend:/app` и **named volume** `frontend_node_modules:/app/node_modules` для dev-HMR; добавить volume `frontend_node_modules` в секцию `volumes` |
| `docs/tech/docker-dev.md` | UPDATE — секция Frontend: реальный Vite, переменная `VITE_API_BASE_URL`, пример `docker compose ... run --rm frontend pnpm run typecheck` (или эквивалент), smoke (curl главной с хоста после `up`) |
| `.env.development.example` | UPDATE — закомментированный или активный пример `VITE_API_BASE_URL=http://localhost:18080` с пояснением |
| `scripts/smoke-frontend-docker.sh` | NEW — bash, `set -euo pipefail`: требует существующий `.env.development` в корне; `docker compose --env-file .env.development build frontend`; `docker compose --env-file .env.development up -d frontend`; короткий sleep; `curl -sf` на `http://127.0.0.1:${FRONTEND_PUBLISH_PORT:-15173}/` и grep на маркер в HTML (например `id="root"` или уникальный комментарий в `index.html`); exit non-zero при фейле; в конце **не** обязательно `down` (чтобы не ломать чужой стек) — можно только `echo` с подсказкой остановить вручную |

## Out of scope

- `.github/workflows/**`, `AGENTS.md`, `.ai/rules/**`, `docs/adr/**`
- `apps/backend/**`, `packages/ptr_coder/**`
- PWA, service worker, manifest, игровые экраны, PixiJS
- Полноценный Playwright в CI (опционально позже; в этой задаче достаточно **curl/smoke script**)
- Изменение корневого `README.md` (если не критично — не трогать)

## Persona

You are working as the **frontend** persona. Apply rules from `.ai/rules/65-personas.md#frontend` in addition to the global repo rules.

Constraints specific to this brief:

- Stack: **React 19 / 18** (совместимо с Vite 6), **Vite 6**, **TypeScript 5**, **pnpm** через Corepack в Docker.
- No `any` in exported component props; keep the UI intentionally minimal.
- API URL only via **`VITE_*`** env — no hardcoded production hosts.

## Acceptance criteria

- [ ] `docker compose --env-file .env.development up --build` поднимает `frontend` с работающим Vite; главная доступна с хоста на опубликованном порту.
- [ ] `VITE_API_BASE_URL` документирован в `docs/tech/docker-dev.md` и `.env.development.example`; дефолт указывает на локальный backend URL (хост `localhost` + порт из дефолта compose), не прод.
- [ ] Команда **TypeScript check через Docker** описана в `docs/tech/docker-dev.md` и реально выполнима (`docker compose ... run ...`).
- [ ] `scripts/smoke-frontend-docker.sh` существует и отражает smoke сценарий (build + up + curl).
- [ ] `docker compose.yml` остаётся валидным; сервис `frontend` по-прежнему `depends_on` backend.

## Test plan

1. После реализации — с корня: `bash scripts/validate-handoff.sh .ai/handoffs/PTR-19-frontend-docker-dev.md` (ожидается OK до добавления секции Result оркестратором — **не редактируй** этот handoff файл).
2. Локально (или CI-агентом): при наличии `.env.development` — `bash scripts/smoke-frontend-docker.sh`.
3. `docker compose --env-file .env.development run --rm --no-deps frontend pnpm run typecheck` (или задокументированная команда) — exit 0.
4. Ручная проверка: открыть в браузере `http://localhost:15173` (или свой `FRONTEND_PUBLISH_PORT`) — виден UI и строка с API base.

## Constraints

- Не добавляй секреты и продакшен URL в репозиторий.
- Vite в контейнере должен слушать **0.0.0.0:5173**.
- Сохраняй **LF** line endings для новых текстовых файлов где уместно (репо использует `.gitattributes`).
- Если bind-mount ломает права на `node_modules`, опирайся на named volume как в `Files in scope`.
- Не вызывай shell из кода приложения — только статическая страница и env.

## Commands

Оркестратор выполнит из **корня репозитория** после твоего прогона (подставь актуальные пути):

| Step | Command |
|------|---------|
| Handoff validate | `bash scripts/validate-handoff.sh .ai/handoffs/PTR-19-frontend-docker-dev.md` |
| Install (если lock неполный) | `cd apps/frontend && corepack enable && pnpm install` |
| Typecheck in Docker | `docker compose --env-file .env.development run --rm --no-deps frontend pnpm run typecheck` |
| Compose config | `docker compose --env-file .env.development config` |
| Smoke (требует `.env.development`) | `bash scripts/smoke-frontend-docker.sh` |

## Result

**Delivered:** Cursor (orchestrator) after partial ptr_coder run (worker exited with error; only early files from LM). Full scaffold, Compose, docs, smoke script, and **`pnpm-lock.yaml`** (via `pnpm install` on host) complete the handoff.

**Validation (orchestrator):** `bash scripts/validate-handoff.sh` OK; `pnpm run typecheck` in `apps/frontend` OK; `docker compose --env-file .env.development.example config` OK. Docker runtime smoke not executed in this session (optional: `bash scripts/smoke-frontend-docker.sh` with real `.env.development`).

**PR:** branch pushed; pull request opened against `main` (Conventional Commits). Ссылка в комментарии Linear к PTR-19.
