from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentType, SubTask
from app.core.logger import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """
You are a quality review agent.

Improve the provided draft for:
- clarity
- grammar
- structure
- professionalism
- readability

Rules:
- preserve meaning
- remove repetition
- improve formatting
- return final polished version only
"""


class CriticAgent(BaseAgent):
    agent_type = AgentType.CRITIC

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
            "Review and improve the content."
        )

        stream = self.llm.stream_complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=400,
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
        if not keys:
            keys = list(data.keys())

        blocks = []

        for key in keys:
            if key in data:
                blocks.append(
                    f"{key}:\n{data[key]}\n"
                )

        return "\n".join(blocks) + "\n" if blocks else ""