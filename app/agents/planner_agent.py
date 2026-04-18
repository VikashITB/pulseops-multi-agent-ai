from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.logger import get_logger
from app.models.schemas import (
    AgentType,
    SubTask,
    TaskPlan,
)

logger = get_logger(__name__)


SYSTEM_PROMPT = """
You are a planning agent.

Convert the user request into a task plan.

Use only these agent types:
retriever, analyzer, writer, critic

Return STRICT JSON only.

Schema:
{
  "reasoning": "brief reason",
  "steps": [
    {
      "step_id": "step-1",
      "agent_type": "retriever",
      "description": "research the topic",
      "depends_on": [],
      "context_keys": [],
      "output_key": "research",
      "priority": 0
    }
  ]
}
"""


class PlannerAgent(BaseAgent):
    agent_type = AgentType.PLANNER

    async def _run(
        self,
        step: SubTask,
        shared_context: dict[str, Any],
        token_queue: asyncio.Queue[str] | None,
    ) -> str:
        try:
            return await self.llm.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=step.description,
                temperature=0.1,
                max_tokens=1000,
            )
        except Exception as exc:
            logger.warning(
                "planner_llm_failed",
                error=str(exc),
            )
            return ""

    @staticmethod
    def parse_plan(
        task_id: str,
        user_request: str,
        raw_output: str,
    ) -> TaskPlan:
        try:
            cleaned = PlannerAgent.extract_json(raw_output)
            data = json.loads(cleaned)

            steps = []

            for item in data.get("steps", []):
                steps.append(SubTask(**item))

            if not steps:
                raise ValueError("No steps returned")

            return TaskPlan(
                task_id=task_id,
                original_request=user_request,
                reasoning=data.get("reasoning", ""),
                steps=steps,
            )

        except Exception as exc:
            logger.warning(
                "planner_fallback_used",
                error=str(exc),
            )

            return PlannerAgent.default_plan(
                task_id,
                user_request,
            )

    @staticmethod
    def extract_json(text: str) -> str:
        if not text:
            raise ValueError("Empty planner response")

        text = text.strip()

        text = re.sub(r"^```json", "", text, flags=re.I)
        text = re.sub(r"^```", "", text)
        text = re.sub(r"```$", "", text)

        match = re.search(r"\{.*\}", text, re.S)

        if match:
            return match.group(0)

        return text

    @staticmethod
    def default_plan(
        task_id: str,
        user_request: str,
    ) -> TaskPlan:
        return TaskPlan(
            task_id=task_id,
            original_request=user_request,
            reasoning="Automatic fallback plan",
            steps=[
                SubTask(
                    step_id="step-1",
                    agent_type=AgentType.RETRIEVER,
                    description=f"Research this topic: {user_request}",
                    depends_on=[],
                    context_keys=[],
                    output_key="research",
                    priority=1,
                ),
                SubTask(
                    step_id="step-2",
                    agent_type=AgentType.ANALYZER,
                    description="Analyze the research findings",
                    depends_on=["step-1"],
                    context_keys=["research"],
                    output_key="analysis",
                    priority=1,
                ),
                SubTask(
                    step_id="step-3",
                    agent_type=AgentType.WRITER,
                    description="Create final polished response",
                    depends_on=["step-2"],
                    context_keys=["analysis"],
                    output_key="final_output",
                    priority=1,
                ),
            ],
        )