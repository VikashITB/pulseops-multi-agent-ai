from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    PLANNER = "planner"
    RETRIEVER = "retriever"
    ANALYZER = "analyzer"
    WRITER = "writer"
    CRITIC = "critic"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class StepStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTask(BaseModel):
    step_id: str
    agent_type: AgentType
    description: str
    depends_on: list[str] = []
    context_keys: list[str] = []
    output_key: str = ""
    priority: int = 0


class SubTaskResult(BaseModel):
    step_id: str
    agent_type: AgentType
    status: StepStatus
    output: str = ""
    error: str | None = None
    duration_ms: int = 0


class TaskPlan(BaseModel):
    task_id: str
    original_request: str
    steps: list[SubTask]
    reasoning: str = ""


class TaskRequest(BaseModel):
    request: str = Field(..., min_length=5, max_length=4000)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    stream_url: str


class TaskSummary(BaseModel):
    task_id: str
    status: TaskStatus
    original_request: str
    plan: TaskPlan | None = None
    results: list[SubTaskResult] = []
    final_output: str = ""
    completed_at: datetime | None = None
    total_duration_ms: int = 0


class SSEEventType(str, Enum):
    TASK_STARTED = "task_started"
    PLAN_READY = "plan_ready"
    STEP_STARTED = "step_started"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


class SSEEvent(BaseModel):
    event: SSEEventType
    task_id: str
    step_id: str | None = None
    agent: AgentType | None = None
    data: Any = None
    message: str = ""