# Generated OpenAPI artifacts

**Do not edit** files in this directory by hand. They are produced from the backend FastAPI OpenAPI schema.

| File | Source |
|------|--------|
| `openapi.json` | `uv run python -m app.export_openapi` in `apps/backend` (or Docker; see [docker-dev.md](../../../../docs/tech/docker-dev.md)) |
| `api-types.ts` | `pnpm run generate:api` (`openapi-typescript` from `openapi.json`) |

## Avoid duplicate DTOs

Application code should **not** introduce parallel TypeScript types that mirror REST payloads. Prefer:

- `import type { paths, operations } from "./api-types"` for route shapes, or
- `createApiClient()` from `src/api/client.ts` (typed `openapi-fetch` client).

## When the REST API changes

1. Update FastAPI routes / models in `apps/backend`.
2. Refresh `openapi.json` (see **OpenAPI — refresh snapshot** in [docker-dev.md](../../../../docs/tech/docker-dev.md)).
3. Run `pnpm run generate:api` (in `apps/frontend`, or via the Docker one-liner in that doc).
4. Run `pnpm run format` in `apps/frontend` so Biome matches CI (`pnpm run lint:ci` checks these files).
5. Commit the updated `openapi.json` and `api-types.ts` together with the backend change (or in the same PR series).

WebSocket message shapes stay **out of** OpenAPI; they are documented separately when the protocol is defined.
