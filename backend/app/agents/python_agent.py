"""Python Agent - Converts natural language to Python data science code (NL2DSCode)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.communication.info_unit import InformationUnit

logger = logging.getLogger(__name__)


class PythonAgent(BaseAgent):
    agent_name = "python_agent"
    agent_role = "Python Agent"

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        schema = ctx.get("schema", "")
        knowledge = ctx.get("knowledge", "")
        notebook_context = ctx.get("notebook_context", "")
        data_source = ctx.get("data_source", "")

        prompt = self._render_prompt(
            "python_generation.j2",
            query=query,
            schema=schema,
            knowledge=knowledge,
            context=notebook_context,
        )

        messages = [self._system_message(), {"role": "user", "content": prompt}]
        code = await self._call_llm(messages)

        code = code.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1]) if len(lines) > 2 else code

        logger.info(f"PythonAgent generated code ({len(code)} chars)")

        return self._create_info_unit(
            content=code,
            action="generate_python_code",
            description=f"Generated Python code for: {query[:80]}",
            data_source=data_source,
        )


python_agent = PythonAgent()
