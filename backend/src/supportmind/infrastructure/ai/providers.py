from __future__ import annotations

from typing import Any

from supportmind.application.ports.interfaces import EnrichmentResult
from supportmind.domain.common.services import CategoryClassifier, PriorityCalculator, SentimentEstimator


class RuleBasedAIProvider:
    """Default AI adapter — deterministic rules. Swap for OpenAI/Claude/Gemini/Ollama later."""

    provider_name = "rule_based"
    model_name = "supportmind-rules-v1"
    prompt_version = "v1"

    async def enrich_ticket(
        self,
        *,
        description: str,
        leaf_code: str,
        path_codes: list[str],
        product_name: str,
        transcript: list[dict[str, Any]],
    ) -> EnrichmentResult:
        priority = PriorityCalculator().calculate(leaf_code=leaf_code, path_codes=path_codes)
        category = CategoryClassifier().classify(leaf_code=leaf_code, path_codes=path_codes)
        sentiment = SentimentEstimator().estimate(leaf_code=leaf_code, path_codes=path_codes)
        path_labels = " → ".join(
            [t.get("answer") or t.get("node_code", "") for t in transcript if t.get("answer")]
        )
        summary = (
            f"Cliente reporta problema en {product_name}. "
            f"Diagnóstico CELU ({leaf_code}): {path_labels or 'sin pasos'}. "
            f"Descripción: {description[:180]}"
        )
        return EnrichmentResult(
            priority=priority,
            category=category,
            sentiment=sentiment,
            summary=summary,
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=self.prompt_version,
            raw={"leaf_code": leaf_code, "path_codes": path_codes},
        )


class OpenAIProviderStub(RuleBasedAIProvider):
    """Placeholder adapter — same contract, ready for real OpenAI wiring."""

    provider_name = "openai"
    model_name = "gpt-4o-mini"


class ClaudeProviderStub(RuleBasedAIProvider):
    provider_name = "claude"
    model_name = "claude-sonnet"


class GeminiProviderStub(RuleBasedAIProvider):
    provider_name = "gemini"
    model_name = "gemini-1.5-flash"


class OllamaProviderStub(RuleBasedAIProvider):
    provider_name = "ollama"
    model_name = "llama3"


def build_ai_provider(name: str) -> RuleBasedAIProvider:
    mapping = {
        "rule_based": RuleBasedAIProvider,
        "openai": OpenAIProviderStub,
        "claude": ClaudeProviderStub,
        "gemini": GeminiProviderStub,
        "ollama": OllamaProviderStub,
    }
    cls = mapping.get(name, RuleBasedAIProvider)
    return cls()
