from app.agents.base_agent import BaseAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.retriever_agent import RetrieverAgent
from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.writer_agent import WriterAgent
from app.agents.critic_agent import CriticAgent

from app.models.schemas import AgentType


AGENT_REGISTRY: dict[AgentType, type[BaseAgent]] = {
    AgentType.PLANNER: PlannerAgent,
    AgentType.RETRIEVER: RetrieverAgent,
    AgentType.ANALYZER: AnalyzerAgent,
    AgentType.WRITER: WriterAgent,
    AgentType.CRITIC: CriticAgent,
}


__all__ = [
    "BaseAgent",
    "PlannerAgent",
    "RetrieverAgent",
    "AnalyzerAgent",
    "WriterAgent",
    "CriticAgent",
    "AGENT_REGISTRY",
]