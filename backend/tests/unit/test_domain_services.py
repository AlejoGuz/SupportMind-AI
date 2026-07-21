from supportmind.domain.common.enums import Priority, Sentiment
from supportmind.domain.common.services import (
    AgentAssignmentPolicy,
    CategoryClassifier,
    FingerprintBuilder,
    IncidentCorrelationPolicy,
    PriorityCalculator,
    SentimentEstimator,
)
from supportmind.domain.common.value_objects import ProblemFingerprint
from supportmind.domain.identity.entities import Agent
from supportmind.domain.common.enums import AgentAvailability, AgentRole
from supportmind.infrastructure.auth.security import hash_password


def test_fingerprint_is_stable():
    a = FingerprintBuilder.build(
        leaf_node_code="no_power",
        product_family="iphone",
        path_codes=["power_start", "charged_30min"],
    )
    b = FingerprintBuilder.build(
        leaf_node_code="no_power",
        product_family="iphone",
        path_codes=["power_start", "charged_30min"],
    )
    assert a == b
    assert isinstance(a, ProblemFingerprint)
    assert len(a.value) == 24


def test_priority_calculator_maps_no_power():
    assert PriorityCalculator().calculate(leaf_code="no_power", path_codes=[]) == Priority.P2


def test_category_classifier():
    assert "Power" in CategoryClassifier().classify(leaf_code="no_power", path_codes=[])


def test_sentiment_negative_on_escalate_path():
    assert (
        SentimentEstimator().estimate(leaf_code="no_power", path_codes=["escalate"])
        == Sentiment.NEGATIVE
    )


def test_assignment_picks_least_loaded_l1():
    busy = Agent(
        email="a@x.com",
        full_name="A",
        hashed_password=hash_password("x"),
        roles=[AgentRole.AGENT_L1],
        availability=AgentAvailability.AVAILABLE,
        open_ticket_count=5,
    )
    free = Agent(
        email="b@x.com",
        full_name="B",
        hashed_password=hash_password("x"),
        roles=[AgentRole.AGENT_L1],
        availability=AgentAvailability.AVAILABLE,
        open_ticket_count=1,
    )
    chosen = AgentAssignmentPolicy().choose([busy, free])
    assert chosen is not None
    assert chosen.email == "b@x.com"


def test_correlation_threshold():
    policy = IncidentCorrelationPolicy(threshold=3, window_seconds=20)
    assert not policy.should_request_alert(2)
    assert policy.should_request_alert(3)
