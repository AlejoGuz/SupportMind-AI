from celery import Celery

from supportmind.config import get_settings

settings = get_settings()

celery_app = Celery(
    "supportmind",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "supportmind.tasks.alerts.*": {"queue": "alerts"},
        "supportmind.tasks.sla.*": {"queue": "sla"},
        "supportmind.tasks.ai.*": {"queue": "ai"},
    },
)


@celery_app.task(name="supportmind.tasks.alerts.evaluate_fingerprint")
def evaluate_fingerprint(fingerprint: str) -> dict:
    """Placeholder async hook for correlation side-effects."""
    return {"fingerprint": fingerprint, "status": "evaluated"}


@celery_app.task(name="supportmind.tasks.sla.check_breaches")
def check_sla_breaches() -> dict:
    return {"checked": True}


@celery_app.task(name="supportmind.tasks.ai.enrich_async")
def enrich_async(ticket_id: str) -> dict:
    return {"ticket_id": ticket_id, "status": "queued"}
