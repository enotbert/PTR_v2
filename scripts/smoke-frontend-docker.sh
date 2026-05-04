#!/usr/bin/env bash
# Smoke: build frontend image, start container, curl HTML marker.
# Requires `.env.development` in repo root (copy from .env.development.example).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE=".env.development"
if [[ ! -f "$ENV_FILE" ]]; then
  printf 'Missing %s — copy from .env.development.example first.\n' "$ENV_FILE" >&2
  exit 2
fi

docker compose --env-file "$ENV_FILE" build frontend
docker compose --env-file "$ENV_FILE" up -d frontend

published="$(docker compose --env-file "$ENV_FILE" port frontend 5173)"
host_port="${published##*:}"

for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${host_port}/" | grep -q 'id="root"'; then
    printf 'OK: frontend responded on http://127.0.0.1:%s/\n' "$host_port"
    printf 'Tip: stop with: docker compose --env-file %s down\n' "$ENV_FILE"
    exit 0
  fi
  sleep 2
done

printf 'FAIL: frontend did not become ready (published %s)\n' "$published" >&2
exit 1
