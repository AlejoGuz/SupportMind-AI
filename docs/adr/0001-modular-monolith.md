# ADR 0001: Modular monolith over microservices

## Status

Accepted

## Context

SupportMind AI is a portfolio product that must demonstrate production-grade architecture without the operational cost of many deployable services.

## Decision

Ship a modular monolith (FastAPI) with clear bounded contexts and Celery workers for async work. Extract services later behind existing ports if needed.

## Consequences

Faster delivery, simpler local DX, still demonstrates Clean Architecture, DI, and horizontal scale of API/workers.
