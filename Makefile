# SupportMind AI helpers

.PHONY: install test api seed customer agent up

install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
	cd apps/web-customer && npm install
	cd apps/web-agent && npm install

test:
	cd backend && . .venv/bin/activate && PYTHONPATH=src pytest -q

api:
	cd backend && . .venv/bin/activate && PYTHONPATH=src uvicorn supportmind.main:app --reload --port 8000

seed:
	cd backend && . .venv/bin/activate && PYTHONPATH=src python -m scripts.seed

customer:
	cd apps/web-customer && npm run dev

agent:
	cd apps/web-agent && npm run dev

up:
	cd infra && docker compose up --build
