FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "fastapi~=0.115.0" \
    "uvicorn[standard]~=0.32.0" \
    "psycopg[binary]~=3.2.0"

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
