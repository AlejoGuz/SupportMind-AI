import pytest

from supportmind.application.ports.interfaces import EnrichmentResult
from supportmind.domain.common.enums import Priority, Sentiment
from supportmind.infrastructure.ai.providers import RuleBasedAIProvider, build_ai_provider


@pytest.mark.asyncio
async def test_rule_based_provider_enriches():
    provider = RuleBasedAIProvider()
    result = await provider.enrich_ticket(
        description="No enciende después de caer",
        leaf_code="no_power",
        path_codes=["power_start", "see_logo"],
        product_name="iPhone 15",
        transcript=[{"prompt": "¿Lo cargó?", "answer": "Sí", "node_code": "charged_30min"}],
    )
    assert isinstance(result, EnrichmentResult)
    assert result.provider == "rule_based"
    assert result.priority in list(Priority)
    assert result.sentiment in list(Sentiment)
    assert "iPhone 15" in result.summary


def test_build_ai_provider_stubs():
    assert build_ai_provider("openai").provider_name == "openai"
    assert build_ai_provider("claude").provider_name == "claude"
    assert build_ai_provider("gemini").provider_name == "gemini"
    assert build_ai_provider("ollama").provider_name == "ollama"
    assert build_ai_provider("unknown").provider_name == "rule_based"
