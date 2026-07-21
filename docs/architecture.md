# SupportMind AI — Architecture Overview

## Style

Modular monolith + Celery workers. Clean Architecture layers:

1. **Presentation** — FastAPI routers + Pydantic DTOs
2. **Application** — use cases + ports
3. **Domain** — entities, value objects, domain services, events
4. **Infrastructure** — SQLAlchemy, Redis, JWT, Celery, AI adapters, storage

## Bounded contexts

identity · conversation · ticketing · alerting · incidents · sla · intelligence · catalog · audit · metrics

## CELU

Guided Decision Engine with multiple-choice only. Outcomes: resolved | escalated | abandoned | blocked_by_incident.

## Correlation

Fingerprint = hash(product_family + leaf_code + path). Redis window 20s / threshold 3 → AlertRequest (human gate) → Incident.

## AI

`AIProviderPort` with `RuleBasedProvider` default. Stubs for OpenAI, Claude, Gemini, Ollama share the same contract.
