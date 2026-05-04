# PTR-22 — Mobile-first PWA app shell (start + network surface)

## Goal

Реализовать **mobile-first app shell** для `apps/frontend`: стартовый / home **placeholder** до tavern flow, **поверхность состояния сети** (браузер offline + доступность API по `VITE_API_BASE_URL`), **touch-first** (минимальные тап-таргеты, нет обязательных hover-only контролов). **Не** добавлять Web App Manifest, service worker, offline gameplay queue, tavern/combat UI.

См. Linear [PTR-22](https://linear.app/ptr-game/issue/PTR-22/realizovat-mobile-first-pwa-app-shell). PTR-19/PTR-15 — **Done**. Изменение `package.json` / `pnpm-lock.yaml` для Playwright (и при необходимости Vitest) **в scope**.

Поведение API: backend уже экспонирует `GET /health` (см. `apps/backend/app/main.py`). Браузер ходит на **хостовый** origin из `import.meta.env.VITE_API_BASE_URL` (как в PTR-19), путь проверки: ``${base.replace(/\/$/, "")}/health``.

## Context

- **UX matrix** (`docs/product/ux_state_matrix_v1.md` §4): стартовый shell, network status как first-class, primary CTA когда online и API ready; offline/API unavailable — явные состояния.
- **CLS**: статусная полоса и hero не должны «прыгать» при смене текста — зафиксируй **минимальную высоту** полосы статуса и основной колонки placeholder (например min-height / grid).
- Пустой `VITE_API_BASE_URL`: показать понятное dev-состояние (например «API base not configured») и считать API недоступным для «ready» CTA.
- Состояния для UI (логика может слегка отличаться в нейминге, смысл обязан быть):
  - **offline** — `navigator.onLine === false` (слушать `online` / `offline`).
  - **online + API OK** — HTTP 200 на `/health` в разумный timeout (3–8s), опционально проверить JSON `status === "ok"`; если `degraded` — всё равно показать как проблему сервиса (**API unavailable** / «limited»), не как полностью готовый raid.
  - **online + API fail** — таймаут, сеть, не-200 → **API unavailable**.

Primary CTA (placeholder): копирай в духе **«Start first raid»** — **disabled** при offline или когда API не готов; при полной готовности — активна (пока без навигации, `type="button"` и `aria-disabled`).

## Files in scope

Создавай и меняй **только** перечисленное:

| Path | Action |
|------|--------|
| `apps/frontend/src/App.tsx` | UPDATE — корневой layout: подключить shell + placeholder |
| `apps/frontend/src/components/AppShell.tsx` | NEW — оболочка: `min-height: 100dvh`, safe-area (`env(safe-area-inset-*)`), колонка для мобильного viewport (max-width ~28–32rem center), семантика `header` / `main` / при необходимости `footer` |
| `apps/frontend/src/components/NetworkStatusBar.tsx` | NEW — компактная полоса: текст + `data-testid="network-status"` (значение: `offline` \| `api-unavailable` \| `ready` \| `checking` \| `no-api-base` — согласуй и задокументируй в тестах) |
| `apps/frontend/src/components/HomePlaceholder.tsx` | NEW — welcome + краткий one-line promise; primary CTA с testid `primary-cta` |
| `apps/frontend/src/hooks/useNetworkAndApiStatus.ts` | NEW — объединяет browser online + периодическую/начальную проверку `/health` с `AbortController` |
| `apps/frontend/src/index.css` | UPDATE — mobile-first база: `body` margin 0, touch targets **min 44px** для кнопок, без hover-only для единственного primary action; фон/контраст читаемый |
| `apps/frontend/index.html` | UPDATE при необходимости — `lang`, meta viewport уже есть; можно улучшить `title` к «PRT» / Pocket Raid Tavern naming по PRD short name |
| `apps/frontend/package.json` | UPDATE — devDependencies: `@playwright/test`, `vitest`, `jsdom` (или среда по умолчанию Vitest 3), `@testing-library/react` при unit-тестах компонента/хука; scripts: `test:unit`, `test:e2e`, `test:e2e:ci` (headless) |
| `apps/frontend/playwright.config.ts` | NEW — проект **mobile** viewport **390×844** (или близко); `baseURL` `http://127.0.0.1:5173`; `webServer: { command: 'pnpm run dev', url: ..., reuseExistingServer: !process.env.CI }` |
| `apps/frontend/e2e/app-shell.spec.ts` | NEW — first load: виден `network-status`, виден primary CTA; опционально сценарий offline через `context.setOffline(true)` и ожидание offline статуса |
| `apps/frontend/vite.config.ts` | UPDATE — при необходимости plugin vitest (`/// <reference types="vitest" />`) |
| `apps/frontend/src/hooks/useNetworkAndApiStatus.test.ts` | NEW — unit-тесты хука (mock `fetch` и `navigator.onLine`) |
| `docs/tech/docker-dev.md` | UPDATE — таблица «Качество»: команды **unit** и **e2e** через `docker compose --env-file .env.development run --rm --no-deps frontend pnpm run …`; если для Playwright в контейнере нужны браузеры — зафиксируй одноразовую установку (`pnpm exec playwright install chromium`) или эквивалент в доке |

## Out of scope

- `manifest.json`, service worker, Workbox, очередь офлайн-действий
- Tavern / raid / combat / PixiJS
- `.github/workflows/**`, `AGENTS.md`, `.ai/rules/**`, новые ADR
- Изменения `docker-compose.yml` / backend — только если без этого невозможно собрать frontend (по умолчанию **не** менять)

## Persona

**Frontend** persona per `.ai/rules/65-personas.md`: React + TypeScript строгий, без `any` в публичных props, доступность (`aria-*` на disabled CTA), только `VITE_*` для URL API.

## Acceptance criteria

- [ ] Shell открывается в **mobile viewport** без заметного **layout shift** при переходе checking → готовое состояние (за счёт зарезервированной высоты полос статуса / контента).
- [ ] Игрок **видит** состояние сети/API (текстовая поверхность, не toast-only).
- [ ] Нет **обязательных** hover-only контролов для основного сценария.
- [ ] **Playwright** first-load mobile + при возможности offline сценарий; **Vitest** для логики хука.
- [ ] В `docs/tech/docker-dev.md` описаны команды проверки через **Docker frontend** (как минимум typecheck уже есть — добавь unit/e2e).

## Test plan

1. `bash scripts/validate-handoff.sh .ai/handoffs/PTR-22-mobile-first-pwa-app-shell.md`
2. Корень: `cd apps/frontend && pnpm install && pnpm run typecheck && pnpm run test:unit && pnpm exec playwright install chromium && pnpm run test:e2e`
3. Docker (при наличии `.env.development`): `docker compose --env-file .env.development run --rm --no-deps frontend pnpm run typecheck` и задокументированные команды unit/e2e.

## Constraints

- Не хардкодить production URL; только `VITE_API_BASE_URL`.
- Не добавлять секреты в репозиторий.
- Сохранять согласованность с существующим **pnpm** и lockfile: после правок `package.json` lockfile должен быть обновлён (если среда не позволяет — явно опиши в итоговом дифе для оркестратора).
- Английские строки UI для кода (репо-конвенция кода на English).

## Commands

Оркестратор выполнит из **корня** и `apps/frontend`:

| Step | Command |
|------|---------|
| Handoff validate | `bash scripts/validate-handoff.sh .ai/handoffs/PTR-22-mobile-first-pwa-app-shell.md` |
| Install | `cd apps/frontend && pnpm install` |
| Typecheck | `pnpm run typecheck` |
| Unit | `pnpm run test:unit` |
| Playwright install (once) | `pnpm exec playwright install chromium` |
| E2E | `pnpm run test:e2e` |
| Docker typecheck | `docker compose --env-file .env.development run --rm --no-deps frontend pnpm run typecheck` |

## Result

**Исполнение:** ptr_coder запускался, но завис без вывода (~12 мин); реализацию завершил оркестратор (Cursor) по этому handoff.

**Валидация:** `pnpm run typecheck`, `pnpm run test:unit`, `pnpm run test:e2e` (Playwright: отдельный порт `5174` + прямой вызов `node node_modules/vite/.../vite.js` в `playwright.config.ts` из-за таймаута `webServer` с `pnpm` в Windows-окружении). E2E мокает `**/health` и не подключается к чужому Vite на `5173` (`reuseExistingServer: false`).

**Артефакты:** app shell, `useNetworkAndApiStatus`, Playwright + Vitest, обновлён `docs/tech/docker-dev.md` (строки unit/e2e).
