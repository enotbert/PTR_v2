FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_LINK_MODE=copy \
    PYTHONPATH=/app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache --group dev

COPY app ./app
COPY tests ./tests

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
