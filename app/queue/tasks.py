from __future__ import annotations

import asyncio

from app.queue.celery_app import celery
from app.core.orchestrator import orchestrator
from app.core.logger import get_logger

logger = get_logger(__name__)


@celery.task(
    bind=True,
    name="app.queue.tasks.run_pipeline_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_pipeline_task(self, task_id: str, user_request: str):
    logger.info(
        "Queue task received",
        task_id=task_id,
    )

    try:
        asyncio.run(execute_pipeline(task_id, user_request))

        return {
            "task_id": task_id,
            "status": "completed",
        }

    except Exception as exc:
        logger.error(
            "Queue task failed",
            task_id=task_id,
            error=str(exc),
        )
        raise exc


async def execute_pipeline(task_id: str, user_request: str):
    entry = orchestrator.tasks.get(task_id)

    if not entry:
        logger.warning(
            "Task entry not found",
            task_id=task_id,
        )
        return

    await orchestrator.run_task(entry, user_request)