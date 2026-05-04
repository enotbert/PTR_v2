# PTR-24 - Service worker and offline shell

## Goal

Implement service worker support and offline shell for `apps/frontend` according to ADR-0009:
- wire `vite-plugin-pwa` (Workbox `generateSW` mode),
- register SW only for production build/preview (not in default `vite dev`),
- precache only static shell assets,
- ensure offline reload serves shell and does not imply gameplay availability.

## Context

- Linear issue: `PTR-24`.
- Dependencies `PTR-16` and `PTR-19` are completed.
- Obsolete references under `docs/foundation/*` must be ignored; use active docs only.
- Current frontend stack already runs in Docker from previous tasks; this task extends it with PWA offline shell behavior.

## Files in scope

Modify only the files needed for PTR-24:

| Path | Action |
|------|--------|
| `apps/frontend/package.json` | UPDATE (add/adjust PWA deps/scripts only if needed) |
| `apps/frontend/pnpm-lock.yaml` | UPDATE if dependency graph changes |
| `apps/frontend/vite.config.ts` | UPDATE (`vite-plugin-pwa` config, Workbox boundaries) |
| `apps/frontend/src/main.tsx` or equivalent app entry | UPDATE SW registration behavior |
| `apps/frontend/src/*` related shell route/fallback | UPDATE only if required for offline reload shell |
| `apps/frontend/index.html` | UPDATE only if required by PWA setup |
| `docs/tech/docker-dev.md` | UPDATE M4 verification steps for SW/offline checks |
| `apps/frontend/e2e/*` | ADD/UPDATE offline smoke if Playwright infra is available in repo |

## Out of scope

- Any gameplay offline queue or optimistic gameplay state sync.
- Caching API/WS responses as successful gameplay operations.
- Changes in `.github/**`, `.ai/rules/**`, `AGENTS.md`, existing ADR files.
- Backend runtime behavior changes unrelated to frontend shell.

## Persona

Frontend persona: React/Vite/TypeScript engineer focused on predictable PWA behavior, explicit network boundaries, and testable offline UX.

## Acceptance criteria

- [ ] SW is active in preview/staging build and not auto-enabled in default `vite dev`.
- [ ] Offline reload shows app shell (not blank document/error page).
- [ ] Navigation/API boundaries are enforced (`/api/` is not treated as app-shell navigation fallback).
- [ ] Documentation describes M4 verification steps for Docker + offline checks.

## Test plan

1. Validate handoff structure.
2. Frontend dependency/install checks (if deps changed).
3. Build frontend and run preview path via Docker-oriented flow where applicable.
4. Manual offline reload check (DevTools offline) for shell rendering.
5. Run Playwright offline smoke if test infra is available in current repo.

## Constraints

- Keep SW registration guarded for production/preview usage.
- Do not cache dynamic gameplay/API/WS as successful data responses.
- Keep `/api/` outside navigation fallback behavior.
- Follow existing repo conventions; avoid unrelated refactors.

## Commands

Orchestrator executes from repo root unless stated:

| Step | Command |
|------|---------|
| Handoff validate | `bash scripts/validate-handoff.sh .ai/handoffs/PTR-24-offline-shell-service-worker.md` |
| Install frontend deps | `cd apps/frontend && pnpm install` |
| Frontend build | `cd apps/frontend && pnpm run build` |
| Frontend typecheck (if script exists) | `cd apps/frontend && pnpm run typecheck` |
| Frontend tests (if script exists) | `cd apps/frontend && pnpm run test` |
| Docker env validation | `docker compose --env-file .env.development config` |
| Docker frontend build | `docker compose --env-file .env.development build frontend` |
| Docker frontend smoke (if script exists) | `bash scripts/smoke-frontend-docker.sh` |
| Playwright offline smoke (if configured) | `cd apps/frontend && pnpm run test:e2e` |

## Result

ptr_coder run was started and applied the core PWA wiring changes, then hung during a later iteration and was stopped by orchestrator.

Completed outcomes:
- Added `vite-plugin-pwa` and generated SW/manifest in frontend build.
- Added production-only SW registration in app entrypoint.
- Added Workbox navigation fallback with `/api/` denylist and API `NetworkOnly` runtime rule.
- Added/updated Playwright offline coverage for shell after runtime offline transition.
- Updated Docker docs with explicit M4 service-worker/offline validation checklist.

Validation executed by orchestrator:
- `bash scripts/validate-handoff.sh .ai/handoffs/PTR-24-offline-shell-service-worker.md`
- `cd apps/frontend && pnpm install`
- `cd apps/frontend && pnpm run build`
- `cd apps/frontend && pnpm run typecheck`
- `cd apps/frontend && pnpm run test:e2e` (2 passed)
- `docker compose --env-file .env.development config`
- `docker compose --env-file .env.development build frontend`
