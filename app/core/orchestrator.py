from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import ulid

from app.agents.writer_agent import WriterAgent
from app.core.pipeline import AsyncPipeline
from app.models.schemas import SSEEvent, SSEEventType, StepStatus, SubTask, SubTaskResult, TaskStatus, TaskSummary
from app.core.logger import get_logger

logger = get_logger(__name__)


def is_simple_prompt(user_request: str) -> bool:
    """Detect if prompt is simple enough for Fast Mode (direct WriterAgent)."""
    # Normalize text
    request_normalized = user_request.lower().strip()
    request_words = request_normalized.split()
    
    # Complex prompt indicators (require Full Mode)
    complex_indicators = {
        "business plan",
        "strategy",
        "market research",
        "pricing",
        "revenue",
        "architecture",
        "compare",
        "detailed report",
    }
    
    # Simple prompt indicators
    simple_indicators = {
        "hello", "hi", "hey",
        "summary", "summarize",
        "caption", "captions",
        "name", "names", "suggest", "ideas",
        "explain", "what is", "how to",
        "define", "meaning",
        "give me", "list", "short",
        "quick", "simple", "basic",
    }
    
    # Priority 1: If contains ANY complex indicators → Full Mode
    for indicator in complex_indicators:
        if indicator in request_normalized:
            return False
    
    # Priority 2: If word_count <= 10 → Fast Mode
    if len(request_words) <= 10:
        return True
    
    # Priority 3: If contains simple indicators → Fast Mode
    for indicator in simple_indicators:
        if indicator in request_normalized:
            return True
    
    # Priority 4: Otherwise → Full Mode
    return False


class TaskEntry:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = TaskStatus.PENDING
        self.event_queue: asyncio.Queue[SSEEvent] = asyncio.Queue(maxsize=1000)
        self.summary: TaskSummary | None = None
        self.created_at = datetime.utcnow()
        self.background_task: asyncio.Task[Any] | None = None


class Orchestrator:
    def __init__(self):
        self.tasks: dict[str, TaskEntry] = {}

    def register(self, user_request: str) -> str:
        """Create task entry + event queue; do NOT dispatch to Celery yet."""
        task_id = ulid.new().str
        self.tasks[task_id] = TaskEntry(task_id)
        logger.info("task_registered", task_id=task_id)
        return task_id

    def dispatch(self, task_id: str, user_request: str) -> None:
        entry = self.tasks.get(task_id)

        if not entry:
            logger.warning("task_not_found_for_dispatch", task_id=task_id)
            return

        entry.background_task = asyncio.create_task(
            self.run_task(entry, user_request)
        )

        logger.info("task_dispatched_local_async", task_id=task_id)

    def submit(self, user_request: str) -> str:
        """Convenience: register + dispatch in one call (legacy path)."""
        task_id = self.register(user_request)
        self.dispatch(task_id, user_request)
        return task_id

    async def run_task(self, entry: TaskEntry, user_request: str):
        entry.status = TaskStatus.RUNNING

        # Determine mode
        mode = "fast" if is_simple_prompt(user_request) else "full"

        await entry.event_queue.put(
            SSEEvent(
                event=SSEEventType.TASK_STARTED,
                task_id=entry.task_id,
                message="Task started",
                mode=mode,
            )
        )

        try:
            # Fast Mode: Simple prompts use direct WriterAgent
            if mode == "fast":
                logger.info(
                    "routing_mode",
                    mode="FAST",
                    prompt=user_request,
                )

                writer = WriterAgent()
                step = SubTask(
                    step_id="fast-mode",
                    agent_type=writer.agent_type,
                    description=user_request,
                    output_key="result",
                )

                result = await writer.run(step, {}, None)

                if result.status == StepStatus.FAILED:
                    raise RuntimeError(result.error)

                summary = TaskSummary(
                    task_id=entry.task_id,
                    status=TaskStatus.COMPLETED,
                    original_request=user_request,
                    plan=None,
                    results=[result],
                    final_output=result.output,
                    completed_at=datetime.utcnow(),
                    total_duration_ms=result.duration_ms,
                )

                # Emit custom TASK_COMPLETED event for FAST mode
                await entry.event_queue.put(
                    SSEEvent(
                        event=SSEEventType.TASK_COMPLETED,
                        task_id=entry.task_id,
                        data={
                            "task_id": entry.task_id,
                            "status": "completed",
                            "result": result.output,
                            "final_output": result.output,
                        },
                        message="Task completed",
                        mode=mode,
                    )
                )
            else:
                # Full Mode: Complex prompts use multi-agent pipeline
                logger.info(
                    "routing_mode",
                    mode="FULL",
                    prompt=user_request,
                )

                pipeline = AsyncPipeline(entry.task_id, entry.event_queue)
                summary = await pipeline.run(user_request)

            entry.summary = summary
            entry.status = summary.status

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                task_id=entry.task_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

            entry.status = TaskStatus.FAILED

            await entry.event_queue.put(
                SSEEvent(
                    event=SSEEventType.TASK_FAILED,
                    task_id=entry.task_id,
                    message=str(exc),
                    mode=mode,
                )
            )

        finally:
            await entry.event_queue.put(
                SSEEvent(
                    event=SSEEventType.TASK_COMPLETED,
                    task_id=entry.task_id,
                    message="__STREAM_END__",
                    mode=mode,
                )
            )

    def get_event_queue(self, task_id: str):
        task = self.tasks.get(task_id)
        return task.event_queue if task else None

    def get_summary(self, task_id: str):
        task = self.tasks.get(task_id)
        return task.summary if task else None

    def get_status(self, task_id: str):
        task = self.tasks.get(task_id)
        return task.status if task else None

    def list_tasks(self):
        return [
            {
                "task_id": task.task_id,
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
            }
            for task in self.tasks.values()
        ]


orchestrator = Orchestrator()