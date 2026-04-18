from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentType, SubTask
from app.core.logger import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """
You are an analysis agent.

Transform raw research into structured insights.

Return:
1. Key themes
2. Important findings
3. Risks or gaps
4. Actionable takeaways

Use markdown formatting.
Be concise and clear.
"""


class AnalyzerAgent(BaseAgent):
    agent_type = AgentType.ANALYZER

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
            "Analyze the information above."
        )

        stream = self.llm.stream_complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.25,
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
        if not keys:
            keys = list(data.keys())

        blocks = []

        for key in keys:
            if key in data:
                blocks.append(
                    f"{key}:\n{data[key]}\n"
                )

        return "\n".join(blocks) + "\n" if blocks else ""