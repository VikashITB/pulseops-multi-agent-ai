from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any

from app.agents import AGENT_REGISTRY
from app.agents.planner_agent import PlannerAgent
from app.models.schemas import (
    AgentType,
    SSEEvent,
    SSEEventType,
    StepStatus,
    SubTask,
    SubTaskResult,
    TaskPlan,
    TaskStatus,
    TaskSummary,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class AsyncPipeline:
    def __init__(self, task_id: str, event_queue: asyncio.Queue[SSEEvent]):
        self.task_id = task_id
        self.event_queue = event_queue
        self.shared_context: dict[str, Any] = {}
        self.results: list[SubTaskResult] = []

    async def run(self, user_request: str) -> TaskSummary:
        started = time.monotonic()

        await self.emit(
            SSEEventType.TASK_STARTED,
            message="Task started",
        )

        plan = await self.create_plan(user_request)

        await self.emit(
            SSEEventType.PLAN_READY,
            data=plan.model_dump(),
            message="Plan created",
        )

        for step in plan.steps:
            logger.info(
                "executing_step",
                step_id=step.step_id,
                agent_type=step.agent_type.value,
            )
            await self.execute_step(step)

        failed = [r for r in self.results if r.status == StepStatus.FAILED]

        status = (
            TaskStatus.PARTIAL
            if failed and len(failed) < len(self.results)
            else TaskStatus.FAILED
            if failed
            else TaskStatus.COMPLETED
        )

        logger.info(
            "creating_task_summary",
            task_id=self.task_id,
            status=status.value,
            steps_count=len(self.results),
        )

        summary = TaskSummary(
            task_id=self.task_id,
            status=status,
            original_request=user_request,
            plan=plan,
            results=self.results,
            final_output=self.get_final_output(),
            completed_at=datetime.utcnow(),
            total_duration_ms=int((time.monotonic() - started) * 1000),
        )

        logger.info(
            "emitting_task_completed",
            task_id=self.task_id,
        )

        try:
            summary_data = summary.model_dump(mode="json", exclude_none=True)
            await self.emit(
                SSEEventType.TASK_COMPLETED,
                data=summary_data,
                message="Task finished",
            )
        except Exception as exc:
            logger.warning(
                "task_summary_emit_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            await self.emit(
                SSEEventType.TASK_COMPLETED,
                data={
                    "task_id": self.task_id,
                    "status": summary.status.value,
                    "result": summary.final_output,
                },
                message="Task finished",
            )

        return summary

    async def create_plan(self, user_request: str) -> TaskPlan:
        planner = PlannerAgent()

        step = SubTask(
            step_id="step-plan",
            agent_type=AgentType.PLANNER,
            description=user_request,
            output_key="plan",
        )

        result = await planner.run(step, self.shared_context)
        self.results.append(result)

        if result.status == StepStatus.FAILED:
            raise RuntimeError(result.error)

        return PlannerAgent.parse_plan(
            self.task_id,
            user_request,
            result.output,
        )

    async def execute_step(self, step: SubTask):
        await self.emit(
            SSEEventType.STEP_STARTED,
            step_id=step.step_id,
            agent=step.agent_type,
            message=f"Running {step.agent_type.value}",
        )

        agent_cls = AGENT_REGISTRY.get(step.agent_type)

        if not agent_cls:
            result = SubTaskResult(
                step_id=step.step_id,
                agent_type=step.agent_type,
                status=StepStatus.FAILED,
                error="Agent not found",
            )
        else:
            agent = agent_cls()
            token_queue = asyncio.Queue(maxsize=100)

            drain = asyncio.create_task(
                self.stream_tokens(step.step_id, token_queue)
            )

            result = await agent.run(
                step,
                dict(self.shared_context),
                token_queue,
            )

            await token_queue.put("__DONE__")
            await drain

        self.results.append(result)

        if result.status == StepStatus.COMPLETED and step.output_key:
            self.shared_context[step.output_key] = result.output

        await self.emit(
            SSEEventType.STEP_COMPLETED
            if result.status == StepStatus.COMPLETED
            else SSEEventType.STEP_FAILED,
            step_id=step.step_id,
            agent=step.agent_type,
            data=result.model_dump(),
        )

    async def stream_tokens(self, step_id: str, queue: asyncio.Queue[str]):
        while True:
            token = await queue.get()

            if token == "__DONE__":
                break

            await self.emit(
                SSEEventType.STEP_PROGRESS,
                step_id=step_id,
                data={"token": token},
            )

    async def emit(
        self,
        event_type: SSEEventType,
        step_id: str | None = None,
        agent: AgentType | None = None,
        data: Any = None,
        message: str = "",
    ):
        await self.event_queue.put(
            SSEEvent(
                event=event_type,
                task_id=self.task_id,
                step_id=step_id,
                agent=agent,
                data=data,
                message=message,
            )
        )

    def get_final_output(self) -> str:
        if "final_output" in self.shared_context:
            return str(self.shared_context["final_output"])

        if self.shared_context:
            return str(list(self.shared_context.values())[-1])

        return ""