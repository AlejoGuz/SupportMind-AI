# ADR 0003: AI provider port

## Status

Accepted

## Context

The product must be ready for OpenAI, Claude, Gemini, and Ollama without redesign.

## Decision

Introduce `AIProviderPort` and ship `RuleBasedAIProvider` as default. Vendor adapters implement the same enrichment contract.

## Consequences

Domain stays free of vendor SDKs. Switching providers is a config change (`AI_PROVIDER`).
