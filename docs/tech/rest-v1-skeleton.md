# REST v1 resource skeleton (PTR-32)

Статус: **skeleton / placeholder** — маршруты и схемы OpenAPI зафиксированы для генерации frontend-клиента; часть операций возвращает `501` с телом `ApiError` (`error`, `message`, опционально `details.tracked_by`).

Границы сущностей и authority — по [data-model-v1-proposal.md](data-model-v1-proposal.md) (§2–§3), без WebSocket и без финальной reward-логики.

## Маршруты и follow-up

| Метод и путь | Поведение сейчас | Реализация |
|---|---|---|
| `GET /v1/taverns/{tavern_id}/state` | Стабильный placeholder (нули + `updated_at`) | PTR-35 |
| `GET /v1/parties/{party_id}` | Placeholder-объект | PTR-37 |
| `POST /v1/parties` | `501` | PTR-37 |
| `GET /v1/raids/{raid_id}` | Placeholder-объект | PTR-37 |
| `POST /v1/raids` | `501` | PTR-37 |
| `GET /v1/players/me/rewards` | Пустой список | Отдельная задача после модели rewards/claims |
| `POST /v1/rewards/{reward_id}/claims` | `501`, `details.tracked_by`: `PTR-32-follow-up` | Завести issue и заменить маркер |
| `POST /v1/invites` | `501` | PTR-55 |
| `GET /v1/invites/by-token/{token}` | Placeholder-объект (не резолвит БД) | PTR-55 |
| `GET /v1/analytics/debug/recent-events` | Пустой список | Отдельная задача (хранилище + ACL) |

Аутентификация: для защищённых маршрутов используется тот же `Authorization: Bearer <session_id>`, что и для `/v1/sessions/*` (см. `apps/backend/app/api/deps.py`).

Регенерация клиента: [docker-dev.md](docker-dev.md) — OpenAPI snapshot и `pnpm run generate:api`.
