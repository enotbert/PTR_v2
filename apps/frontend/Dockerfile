FROM node:22-bookworm-slim

WORKDIR /app

# Vite/React package manifests are introduced in bootstrap follow-up tasks.
# Build context intentionally minimal so `docker compose build` succeeds before apps/frontend/package.json lands.
COPY README.md ./README.md

EXPOSE 5173

CMD ["sh", "-c", "printf '%s\\n' 'Frontend scaffold: expose default Vite port 5173. See docs/tech/docker-dev.md.' && exec tail -f /dev/null"]
