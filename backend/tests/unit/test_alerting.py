import pytest

from supportmind.domain.alerting.entities import AlertRequest, Incident
from supportmind.domain.common.enums import AlertRequestStatus, IncidentStatus
from supportmind.infrastructure.cache.correlation import RedisCorrelationService
from uuid import uuid4


@pytest.mark.asyncio
async def test_in_memory_correlation_counts_within_window():
    corr = RedisCorrelationService(redis=None)
    fp = "abc123"
    c1 = await corr.record_and_count(fp, uuid4(), 20)
    c2 = await corr.record_and_count(fp, uuid4(), 20)
    c3 = await corr.record_and_count(fp, uuid4(), 20)
    assert c1 == 1
    assert c2 == 2
    assert c3 == 3


@pytest.mark.asyncio
async def test_alert_lock_only_once():
    corr = RedisCorrelationService(redis=None)
    assert await corr.try_acquire_alert_lock("fp1", 30) is True
    assert await corr.try_acquire_alert_lock("fp1", 30) is False


def test_alert_request_accept_reject():
    req = AlertRequest(
        fingerprint="f",
        problem_code="no_power",
        ticket_count=3,
        window_seconds=20,
    )
    req.accept()
    assert req.status == AlertRequestStatus.ACCEPTED
    req2 = AlertRequest(
        fingerprint="f2",
        problem_code="no_power",
        ticket_count=3,
        window_seconds=20,
    )
    req2.reject()
    assert req2.status == AlertRequestStatus.REJECTED


def test_incident_resolve():
    inc = Incident(
        number="INC-2026-000001",
        title="t",
        fingerprint="f",
        problem_code="no_power",
        status=IncidentStatus.ACTIVE,
        public_message="msg",
        created_from_alert_id=None,
        created_by=uuid4(),
    )
    inc.resolve()
    assert inc.status == IncidentStatus.RESOLVED
    assert inc.resolved_at is not None
