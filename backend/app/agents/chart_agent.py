"""Chart Agent - Converts natural language to chart specifications (NL2VIS)."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.communication.info_unit import InformationUnit

logger = logging.getLogger(__name__)


class ChartAgent(BaseAgent):
    agent_name = "chart_agent"
    agent_role = "Chart Agent"

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        data_info = ctx.get("data_info", "")
        dsl = ctx.get("dsl", "")
        data_source = ctx.get("data_source", "")

        prompt = self._render_prompt(
            "chart_generation.j2",
            query=query,
            data_info=data_info,
            dsl=dsl,
        )

        messages = [self._system_message(), {"role": "user", "content": prompt}]

        try:
            chart_spec = await self._call_llm_json(messages)
        except Exception:
            raw = await self._call_llm(messages)
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1])
            chart_spec = json.loads(raw)

        logger.info(f"ChartAgent generated spec with keys: {list(chart_spec.keys())}")

        return self._create_info_unit(
            content=chart_spec,
            action="generate_chart",
            description=f"Generated chart for: {query[:80]}",
            data_source=data_source,
        )


chart_agent = ChartAgent()
