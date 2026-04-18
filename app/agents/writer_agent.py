from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentType, SubTask
from app.core.logger import get_logger

logger = get_logger(__name__)


CASUAL_PROMPT = """
You are a helpful AI assistant.

Respond naturally, briefly, and conversationally.

For casual greetings and simple questions:
- Be friendly and direct
- Keep responses short (1-3 sentences)
- No markdown formatting needed
- No structured sections
- Just answer naturally

Output only final answer.
"""

GENERAL_PROMPT = """
You are a helpful AI assistant.

Provide clear, accurate, and well-structured answers.

For factual and general questions:
- Use clear, concise language
- Organize information logically
- Use bullet points for lists when helpful
- Include relevant details but stay focused
- Be direct and informative

Output only final answer.
"""

STARTUP_IDEAS_PROMPT = """
You are a YC-style startup idea generator. Generate sharp, investor-quality startup opportunities.

FOR EACH IDEA, USE THIS FRAMEWORK:

## Idea Name
- Niche (specific market segment)
- Problem (painful, recurring, urgent)
- Buyer (clear decision-maker with budget)
- Revenue model (monetizable quickly)
- Why now (current trend/timing)
- MVP (buildable in 30 days)

PREFERRED VERTICALS:
- India-focused opportunities
- B2B SaaS for SMBs
- AI tools for specific workflows
- College/student market
- Creator economy infrastructure
- Fintech operations
- Healthcare operations
- Developer tools

AVOID:
- Generic wellness apps
- Vague sustainability ideas
- Consumer apps without clear monetization
- Ideas requiring massive user acquisition

QUALITY STANDARDS:
- Ideas must feel like they could get into YC
- Specific niche, not broad horizontal plays
- Problem must be painful and recurring
- Buyer must have budget and clear ROI
- Revenue model should enable quick monetization
- Timing argument must be compelling
- MVP must be achievable in 30 days with small team

Generate 5-7 distinct ideas unless specified otherwise.

Output only final answer.
"""

GTM_PROMPT = """
You are a founder-first startup operator and GTM strategist.

Your job is to convert raw analysis into realistic, execution-focused recommendations.

MANDATORY RULES:
1. No generic advice or consultant fantasy.
2. Every numeric estimate MUST begin with "Assumption: "
3. Recommend realistic ICP: mid-market before Fortune 500
4. Competitors must be market-relevant by geography and segment
5. Prefer actionable channel tactics over broad statements
6. Show prioritization logic (why X before Y)
7. Roadmaps must be complete and execution-focused
8. Use concise markdown bullets

WHEN REQUEST IS ABOUT STARTUP / GTM / SaaS / GROWTH / LAUNCH:

Return sections in this order:

## Executive Summary
2-4 bullets on biggest growth opportunities with prioritization logic.

## ICP (Ideal Customer Profile)
- Company size (start with mid-market: 50-500 employees)
- Buyer role (specific title, not "decision maker")
- Industry (specific vertical)
- Pain point (concrete problem they face today)
- Budget readiness (typical budget range)

## Pricing Strategy
- Free / Starter / Growth / Enterprise tiers
- Suggested price ranges (e.g., "$49-99/mo for Growth")
- Expansion logic (how customers upgrade)

## Unit Economics
Assumption-based estimates:
- CAC by channel (e.g., "Assumption: $500-800 for SEO, $2k-5k for outbound")
- LTV range (e.g., "Assumption: $1,200-2,400 based on $100-200 ARPU")
- Payback period (months to recover CAC)
- Sales cycle (typical deal length)

## Top Competitors
For top 3:
- Name (market-relevant by geography/segment)
- Strength (what they do well)
- Weakness (where they struggle)
- Wedge (where you win specifically)

## Channel Priority
Rank channels with logic:
1. Fastest acquisition (with specific tactic)
2. Lowest CAC (with range)
3. Highest scale potential (with constraint)

## Risks
Top 5 risks + concrete mitigation (not "monitor" but specific action).

## 30 / 60 / 90 Day Plan
Execution-focused milestones:
- Month 1: Concrete deliverables
- Month 2: Measurable outcomes
- Month 3: Scale targets

## KPI Dashboard
- Leads (by channel)
- CAC (by channel)
- Demo conversion rate
- Win rate
- MRR
- Churn

STYLE RULES:
- Think founder-first: what would YOU do tomorrow morning
- Use numbers where useful, always with "Assumption:" prefix
- One insight per bullet
- No filler words or corporate jargon
- No intro/outro text

Output only final answer.
"""


class WriterAgent(BaseAgent):
    agent_type = AgentType.WRITER

    def classify_prompt(self, prompt: str) -> str:
        """
        Classify prompt type to determine appropriate response mode.

        Returns: 'casual', 'general', 'startup_ideas', or 'business_strategy'
        """
        prompt_lower = prompt.lower()

        # Casual/social keywords
        casual_keywords = [
            'hello', 'hi', 'hey', 'how are you', 'how are you doing',
            'thanks', 'thank you', 'appreciate', 'joke', 'who are you',
            'what can you do', 'help me', 'please help', 'can you help'
        ]

        # Startup ideas keywords (check BEFORE business_strategy)
        startup_ideas_keywords = [
            'idea', 'ideas', 'startup ideas', 'business ideas',
            'app ideas', 'niche ideas', 'opportunities'
        ]

        # Business strategy keywords (GTM, pricing, etc.)
        business_strategy_keywords = [
            'gtm', 'go-to-market', 'go to market', 'pricing',
            'cac', 'ltv', 'pmf', 'product-market fit',
            'competitors', 'competitor analysis', 'launch plan',
            'sales cycle', 'payback', 'launch strategy',
            'fundraising strategy', 'sales plan', 'unit economics'
        ]

        # Check for casual/social
        for keyword in casual_keywords:
            if keyword in prompt_lower:
                return 'casual'

        # Check for startup ideas (must come before business_strategy)
        for keyword in startup_ideas_keywords:
            if keyword in prompt_lower:
                return 'startup_ideas'

        # Check for business strategy
        for keyword in business_strategy_keywords:
            if keyword in prompt_lower:
                return 'business_strategy'

        # Default to general
        return 'general'

    def get_system_prompt(self, prompt_type: str) -> str:
        """Return appropriate system prompt based on classification."""
        if prompt_type == 'casual':
            return CASUAL_PROMPT
        elif prompt_type == 'startup_ideas':
            return STARTUP_IDEAS_PROMPT
        elif prompt_type == 'business_strategy':
            return GTM_PROMPT
        else:
            return GENERAL_PROMPT

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

        # Classify prompt type
        full_prompt = f"Task: {step.description}\n\n{context}Write the final response."
        prompt_type = self.classify_prompt(full_prompt)
        system_prompt = self.get_system_prompt(prompt_type)

        logger.info(f"Prompt classified as: {prompt_type}")

        stream = self.llm.stream_complete(
            system_prompt=system_prompt,
            user_prompt=full_prompt,
            temperature=0.45,
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