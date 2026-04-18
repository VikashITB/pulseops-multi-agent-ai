from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from app.core.llm_provider import BaseLLMProvider, get_llm_provider
from app.models.schemas import (
    AgentType,
    StepStatus,
    SubTask,
    SubTaskResult,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    agent_type: AgentType

    def __init__(self, llm: BaseLLMProvider | None = None):
        self._llm = llm
        self.log = get_logger(self.__class__.__name__)

    @property
    def llm(self) -> BaseLLMProvider:
        if self._llm is None:
            self._llm = get_llm_provider()
        return self._llm

    async def run(
        self,
        step: SubTask,
        shared_context: dict[str, Any],
        token_queue: asyncio.Queue[str] | None = None,
    ) -> SubTaskResult:
        started = time.monotonic()

        try:
            output = await self._run(step, shared_context, token_queue)

            return SubTaskResult(
                step_id=step.step_id,
                agent_type=self.agent_type,
                status=StepStatus.COMPLETED,
                output=output,
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        except Exception as exc:
            logger.exception("Agent failed", error=str(exc))

            return SubTaskResult(
                step_id=step.step_id,
                agent_type=self.agent_type,
                status=StepStatus.FAILED,
                error=str(exc),
                duration_ms=int((time.monotonic() - started) * 1000),
            )

    @abstractmethod
    async def _run(
        self,
        step: SubTask,
        shared_context: dict[str, Any],
        token_queue: asyncio.Queue[str] | None,
    ) -> str:
        ...

    async def stream_response(
        self,
        stream: AsyncGenerator[str, None],
        token_queue: asyncio.Queue[str] | None,
        prefix: str = "",
    ) -> str:
        chunks: list[str] = []

        async for token in stream:
            chunks.append(token)

            if token_queue:
                try:
                    token_queue.put_nowait(f"{prefix}{token}")
                except asyncio.QueueFull:
                    pass

        return "".join(chunks)