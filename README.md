# SupportMind AI

Intelligent ITSM platform with CELU guided chatbot.

## Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, JWT
- Frontend: React, TypeScript, Vite, TailwindCSS, React Query, Zustand, Recharts
- Infra: Docker Compose, Nginx, GitHub Actions, MinIO

## Quick start

```bash
cp .env.example .env
cd infra && docker compose up --build
```

- Customer portal: http://localhost:5173
- Agent portal: http://localhost:5174
- API docs: http://localhost:8000/docs
- Nginx gateway: http://localhost:8080

### Demo credentials

| Email | Password | Role |
|---|---|---|
| admin@supportmind.ai | Admin123! | Admin |
| lucia@supportmind.ai | Agent123! | Agent L1 |
| marco@supportmind.ai | Agent123! | Agent L1 |

## Local development (API)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export PYTHONPATH=src
# start postgres/redis via docker compose
python -m scripts.seed
uvicorn supportmind.main:app --reload
```

## Architecture

See [docs/architecture.md](docs/architecture.md) and ADRs under `docs/adr/`.

CELU uses multiple-choice decision trees only (no free text). Escalation creates tickets automatically, correlates fingerprints in a 20s window, and opens human-approved Alert Requests before creating parent Incidents.
