from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentType, SubTask
from app.core.logger import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """
You are a startup content specialist.

Transform analysis into actionable, data-driven business output.

Format based on context:
- Executive summary → 3-5 bullet insights + 1 recommendation
- Strategy brief → Problem → Data-backed solution → Implementation steps
- Market analysis → Key metrics → Competitive gap → Opportunity sizing
- Product pitch → Problem → Solution → Traction → Ask

Style guidelines:
- Lead with specific numbers/metrics from analysis
- Use present tense for current state, future for recommendations
- Replace "we believe" with "data indicates"
- Cut: "leverage", "synergy", "paradigm", "game-changer"
- Use: "improves", "reduces", "increases", "enables"
- One sentence per line for readability
- End with concrete next step or metric target

Output only the final content. No intro/outro fluff.
"""


class WriterAgent(BaseAgent):
    agent_type = AgentType.WRITER

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
            "Write the final response."
        )

        stream = self.llm.stream_complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.7,
            max_tokens=700,
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