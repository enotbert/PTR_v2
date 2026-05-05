import createClient from "openapi-fetch";

import type { paths } from "../generated/api-types";

/** Typed REST client for the backend OpenAPI schema (`src/generated/api-types.ts`). */
export function createApiClient(baseUrl: string) {
  const normalized = baseUrl.trim().replace(/\/+$/, "");
  return createClient<paths>({ baseUrl: normalized });
}

/** Session-authenticated client (Bearer `session_id`). */
export function createBearerApiClient(baseUrl: string, sessionId: string) {
  const normalized = baseUrl.trim().replace(/\/+$/, "");
  return createClient<paths>({
    baseUrl: normalized,
    headers: { Authorization: `Bearer ${sessionId}` },
  });
}
