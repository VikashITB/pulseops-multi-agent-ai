from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.logger import get_logger
from app.core.orchestrator import orchestrator
from app.models.schemas import TaskRequest, TaskResponse
from app.queue.tasks import process_batch_task
from app.services.batch_buffer import BatchBuffer
from app.services.streaming import event_generator

logger = get_logger(__name__)

router = APIRouter(tags=["tasks"])


@router.post("/task", response_model=TaskResponse)
async def create_task(request: Request, payload: TaskRequest):
    task_id = orchestrator.register(payload.request)

    orchestrator.dispatch(task_id, payload.request)

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Task submitted successfully",
        stream_url=f"/api/v1/stream/{task_id}",
    )


@router.get("/task/{task_id}")
async def get_task(task_id: str):
    summary = orchestrator.get_summary(task_id)

    if summary:
        return summary

    status = orchestrator.get_status(task_id)

    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "status": status,
    }


@router.get("/stream/{task_id}")
async def stream_task(task_id: str):
    queue = orchestrator.get_event_queue(task_id)

    if queue is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return StreamingResponse(
        event_generator(queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/tasks")
async def list_tasks():
    return orchestrator.list_tasks()