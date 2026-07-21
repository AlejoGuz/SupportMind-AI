FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/README.md* /app/backend/
COPY backend/src /app/backend/src
COPY backend/alembic /app/backend/alembic
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/scripts /app/backend/scripts

WORKDIR /app/backend
RUN pip install --no-cache-dir -e ".[dev]"

ENV PYTHONPATH=/app/backend/src:/app/backend
EXPOSE 8000

CMD ["uvicorn", "supportmind.main:app", "--host", "0.0.0.0", "--port", "8000"]
