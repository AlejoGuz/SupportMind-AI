from __future__ import annotations

from supportmind.domain.common.enums import Priority, Sentiment
from supportmind.domain.common.value_objects import ProblemFingerprint
from supportmind.domain.identity.entities import Agent


class FingerprintBuilder:
    @staticmethod
    def build(*, leaf_node_code: str, product_family: str, path_codes: list[str]) -> ProblemFingerprint:
        return ProblemFingerprint.build(
            leaf_node_code=leaf_node_code,
            product_family=product_family,
            path_codes=path_codes,
        )


class PriorityCalculator:
    """Rule-based priority; AI provider can override later via enrichment port."""

    SEVERITY_MAP = {
        "power_no_logo": Priority.P1,
        "boot_loop": Priority.P1,
        "login_500": Priority.P1,
        "no_power": Priority.P2,
        "battery_drain": Priority.P3,
        "screen_crack": Priority.P3,
        "general": Priority.P4,
    }

    def calculate(self, *, leaf_code: str, path_codes: list[str]) -> Priority:
        for code in [leaf_code, *reversed(path_codes)]:
            key = code.lower()
            if key in self.SEVERITY_MAP:
                return self.SEVERITY_MAP[key]
        return Priority.P3


class CategoryClassifier:
    CATEGORY_MAP = {
        "power": "Hardware / Power",
        "boot": "Hardware / Boot",
        "battery": "Hardware / Battery",
        "screen": "Hardware / Display",
        "login": "Software / Authentication",
        "network": "Software / Connectivity",
    }

    def classify(self, *, leaf_code: str, path_codes: list[str]) -> str:
        tokens = [leaf_code.lower(), *[c.lower() for c in path_codes]]
        for token in tokens:
            for prefix, category in self.CATEGORY_MAP.items():
                if prefix in token:
                    return category
        return "General / Other"


class SentimentEstimator:
    NEGATIVE_HINTS = {"no_power", "boot_loop", "login_500", "escalate", "broken"}

    def estimate(self, *, leaf_code: str, path_codes: list[str]) -> Sentiment:
        joined = " ".join([leaf_code, *path_codes]).lower()
        if any(h in joined for h in self.NEGATIVE_HINTS):
            return Sentiment.NEGATIVE
        return Sentiment.NEUTRAL


class AgentAssignmentPolicy:
    def choose(self, agents: list[Agent]) -> Agent | None:
        available = [a for a in agents if a.is_l1_available()]
        if not available:
            return None
        return sorted(available, key=lambda a: (a.open_ticket_count, a.full_name))[0]


class IncidentCorrelationPolicy:
    def __init__(self, *, threshold: int = 3, window_seconds: int = 20) -> None:
        self.threshold = threshold
        self.window_seconds = window_seconds

    def should_request_alert(self, count_in_window: int) -> bool:
        return count_in_window >= self.threshold
