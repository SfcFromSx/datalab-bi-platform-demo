"""Report Agent - Generates analysis reports in Markdown."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.communication.info_unit import InformationUnit

logger = logging.getLogger(__name__)

REPORT_PROMPT = """You are an expert data analyst creating a comprehensive analysis report.

{context}

Generate a professional Markdown report that includes:
1. **Executive Summary** - Key findings in 2-3 sentences
2. **Data Overview** - Description of the dataset analyzed
3. **Key Findings** - Detailed analysis with specific numbers
4. **Visualizations** - Describe recommended charts (the chart agent will create them)
5. **Recommendations** - Actionable next steps based on findings
6. **Methodology** - Brief description of analysis approach

User request: {query}

Write the report in clean Markdown format."""


class ReportAgent(BaseAgent):
    agent_name = "report_agent"
    agent_role = "Report Agent"

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        analysis_context = ctx.get("analysis_context", "No analysis context available")
        data_source = ctx.get("data_source", "")

        prompt = REPORT_PROMPT.format(context=analysis_context, query=query)
        messages = [self._system_message(), {"role": "user", "content": prompt}]
        report = await self._call_llm(messages, temperature=0.3, max_tokens=8192)

        return self._create_info_unit(
            content=report,
            action="generate_report",
            description=f"Analysis report for: {query[:80]}",
            data_source=data_source,
        )


report_agent = ReportAgent()
