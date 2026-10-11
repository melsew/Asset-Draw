"""Celery application. Runs from the same image as the API (spec section 4).

Start with:  celery -A worker.celery_app worker --loglevel=INFO
Real jobs (spec section 19) are added in later phases.
"""
from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery("asset_draw", broker=_settings.redis_url, backend=_settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={},
)


@celery_app.task(name="system.ping")
def ping() -> str:
    """Smoke-test task proving the worker is wired to the broker."""
    return "pong"
