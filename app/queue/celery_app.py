from __future__ import annotations

from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun
from kombu import Exchange, Queue

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def create_celery() -> Celery:
    celery = Celery(
        "pulseops_ai",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["app.queue.tasks"],
    )

    celery.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        task_default_queue="default",

        task_queues=(
            Queue("default", Exchange("default"), routing_key="default"),
            Queue("priority", Exchange("priority"), routing_key="priority"),
            Queue("llm", Exchange("llm"), routing_key="llm"),
        ),

        task_routes={
            "app.queue.tasks.run_pipeline_task": {
                "queue": "llm"
            }
        },

        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,

        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=50,

        result_expires=3600,
    )

    return celery


celery = create_celery()


@task_prerun.connect
def on_task_start(task_id=None, task=None, **kwargs):
    logger.info(
        "Task started",
        task_id=task_id,
        task_name=task.name if task else None,
    )


@task_postrun.connect
def on_task_finish(task_id=None, task=None, state=None, **kwargs):
    logger.info(
        "Task finished",
        task_id=task_id,
        task_name=task.name if task else None,
        state=state,
    )


@task_failure.connect
def on_task_failed(task_id=None, exception=None, **kwargs):
    logger.error(
        "Task failed",
        task_id=task_id,
        error=str(exception),
    )