"""Insight Agent - Discovers data insights and patterns (NL2Insight)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.communication.info_unit import InformationUnit

logger = logging.getLogger(__name__)


class InsightAgent(BaseAgent):
    agent_name = "insight_agent"
    agent_role = "Insight Agent"

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        data_info = ctx.get("data_info", "")
        analysis_context = ctx.get("analysis_context", "")
        data_source = ctx.get("data_source", "")

        prompt = self._render_prompt(
            "insight_generation.j2",
            query=query,
            data_info=data_info,
            context=analysis_context,
        )

        messages = [self._system_message(), {"role": "user", "content": prompt}]
        insights = await self._call_llm(messages, temperature=0.3)

        logger.info(f"InsightAgent generated insights ({len(insights)} chars)")

        return self._create_info_unit(
            content=insights,
            action="discover_insights",
            description=f"Discovered insights for: {query[:80]}",
            data_source=data_source,
        )


insight_agent = InsightAgent()
