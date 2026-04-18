from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentType, SubTask
from app.core.logger import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """
You are a research agent.

Collect accurate, relevant, and structured information for the requested topic.

Rules:
- focus on facts
- use bullet points when useful
- concise but useful
- no filler text
"""


class RetrieverAgent(BaseAgent):
    agent_type = AgentType.RETRIEVER

    async def _run(
        self,
        step: SubTask,
        shared_context: dict[str, Any],
        token_queue: asyncio.Queue[str] | None,
    ) -> str:
        context = self.build_context(
            step.context_keys,
            shared_context,
        )

        prompt = (
            f"Task: {step.description}\n\n"
            f"{context}"
            "Return research findings."
        )

        stream = self.llm.stream_complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3,
            max_tokens=500,
        )

        return await self.stream_response(
            stream,
            token_queue,
            prefix=f"[{step.step_id}] ",
        )

    def build_context(
        self,
        keys: list[str],
        data: dict[str, Any],
    ) -> str:
        blocks = []

        for key in keys:
            if key in data:
                blocks.append(
                    f"{key}:\n{data[key]}\n"
                )

        return "\n".join(blocks) + "\n" if blocks else ""