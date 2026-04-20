from __future__ import annotations

import asyncio

from app.core.logger import get_logger
from app.core.orchestrator import orchestrator
from app.queue.celery_app import celery

logger = get_logger(__name__)


@celery.task(
    bind=True,
    name="app.queue.tasks.run_pipeline_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_pipeline_task(self, task_id: str, user_request: str):
    logger.info("queue_task_received", task_id=task_id)

    try:
        asyncio.run(execute_pipeline(task_id, user_request))
        return {"task_id": task_id, "status": "completed"}

    except Exception as exc:
        logger.error("queue_task_failed", task_id=task_id, error=str(exc))
        raise


@celery.task(
    bind=True,
    name="app.queue.tasks.process_batch_task",
    autoretry_for=(),
)
def process_batch_task(self, batch: list[dict]):
    batch_size = len(batch)

    logger.info(
        "batch_task_received",
        batch_size=batch_size,
    )

    succeeded = 0
    failed = 0

    for index, item in enumerate(batch, start=1):
        task_id: str = item.get("task_id", "<unknown>")
        user_request: str = item.get("user_request", "")

        logger.info(
            "batch_item_starting",
            batch_index=index,
            batch_size=batch_size,
            task_id=task_id,
        )

        try:
            asyncio.run(execute_pipeline(task_id, user_request))
            succeeded += 1
            logger.info(
                "batch_item_completed",
                batch_index=index,
                batch_size=batch_size,
                task_id=task_id,
            )

        except Exception as exc:
            failed += 1
            logger.error(
                "batch_item_failed",
                batch_index=index,
                batch_size=batch_size,
                task_id=task_id,
                error=str(exc),
            )

    logger.info(
        "batch_task_finished",
        batch_size=batch_size,
        succeeded=succeeded,
        failed=failed,
    )

    return {
        "batch_size": batch_size,
        "succeeded": succeeded,
        "failed": failed,
    }


async def execute_pipeline(task_id: str, user_request: str):
    entry = orchestrator.tasks.get(task_id)

    if not entry:
        logger.warning("task_entry_not_found", task_id=task_id)
        return

    await orchestrator.run_task(entry, user_request)