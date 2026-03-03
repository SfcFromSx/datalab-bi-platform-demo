"""EDA Agent - Performs exploratory data analysis."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.communication.info_unit import InformationUnit

logger = logging.getLogger(__name__)

EDA_PROMPT = """You are an expert data scientist performing exploratory data analysis (EDA).

{data_info}

Generate Python code that performs comprehensive EDA:
1. Display basic statistics (shape, dtypes, describe)
2. Check for missing values and duplicates
3. Analyze distributions of numerical columns
4. Analyze value counts of categorical columns
5. Check for correlations between numerical columns
6. Print a clear summary of findings

Use pandas. Print results with clear headers. Store the summary in a variable called `eda_summary`.

User request: {query}

Respond with ONLY Python code, no markdown fences."""


class EDAAgent(BaseAgent):
    agent_name = "eda_agent"
    agent_role = "EDA Agent"

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        data_info = ctx.get("data_info", "No data description available")
        data_source = ctx.get("data_source", "")

        prompt = EDA_PROMPT.format(data_info=data_info, query=query)
        messages = [self._system_message(), {"role": "user", "content": prompt}]
        code = await self._call_llm(messages)

        code = code.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1]) if len(lines) > 2 else code

        return self._create_info_unit(
            content=code,
            action="exploratory_data_analysis",
            description=f"EDA for: {query[:80]}",
            data_source=data_source,
        )


eda_agent = EDAAgent()
