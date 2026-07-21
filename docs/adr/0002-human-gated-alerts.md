# ADR 0002: Human-gated incident creation

## Status

Accepted

## Context

CELU can detect correlated tickets quickly (3 in 60s). Auto-creating incidents risks false positives.

## Decision

Always create an `AlertRequest` for human accept/reject. Never auto-create incidents.

## Consequences

Slightly more agent workload; strong audit trail; safer demos and production posture.
