"""SQL Agent - Converts natural language to SQL queries (NL2SQL)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.communication.info_unit import InformationUnit

logger = logging.getLogger(__name__)


class SQLAgent(BaseAgent):
    agent_name = "sql_agent"
    agent_role = "SQL Agent"

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        schema = ctx.get("schema", "No schema available")
        knowledge = ctx.get("knowledge", "")
        dsl = ctx.get("dsl", "")
        data_source = ctx.get("data_source", "")

        prompt = self._render_prompt(
            "sql_generation.j2",
            query=query,
            schema=schema,
            knowledge=knowledge,
            dsl=dsl,
        )

        messages = [self._system_message(), {"role": "user", "content": prompt}]
        sql_query = await self._call_llm(messages)

        sql_query = sql_query.strip()
        if sql_query.startswith("```"):
            lines = sql_query.split("\n")
            sql_query = "\n".join(lines[1:-1]) if len(lines) > 2 else sql_query

        logger.info(f"SQLAgent generated query: {sql_query[:100]}...")

        return self._create_info_unit(
            content=sql_query,
            action="generate_sql_query",
            description=f"Generated SQL query for: {query[:80]}",
            data_source=data_source,
        )


sql_agent = SQLAgent()
