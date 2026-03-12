"""ChatBI Agent - Streams NL-to-SQL, execution, and optional chart generation."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

from app.agents.base import BaseAgent
from app.execution import sql_executor
from app.llm.client import llm_client

logger = logging.getLogger(__name__)

_VIZ_KEYWORDS = frozenset(
    ["chart", "plot", "graph", "visualize", "visualization", "show me a", "draw", "diagram"]
)


class ChatBIAgent(BaseAgent):
    agent_name = "chat_bi_agent"
    agent_role = "Chat BI Agent"

    async def stream_query(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Yield structured step dicts consumed by the SSE endpoint.

        Step types: thinking, sql, executing, data, chart, answer, error.
        """
        ctx = context or {}
        viz_requested = any(kw in query.lower() for kw in _VIZ_KEYWORDS)

        yield {"type": "thinking", "content": "Analyzing your question..."}

        base_prompt = query
        nb_context = ctx.get("notebook_context")
        if nb_context:
            base_prompt += f"\n\nNotebook context:\n{nb_context}"

        sql_query = ""
        try:
            async for chunk in self._generate_sql_stream(base_prompt, ctx):
                sql_query += chunk
                yield {"type": "sql", "content": _strip_sql_fences(sql_query)}
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            yield {"type": "error", "content": f"Failed to generate SQL: {e}"}
            return

        sql_query = _strip_sql_fences(sql_query)
        if not sql_query.strip():
            yield {"type": "error", "content": "LLM returned empty SQL."}
            return

        yield {"type": "executing", "content": "Running query..."}

        try:
            result = sql_executor.execute_isolated(
                sql_query,
                tables=ctx.get("raw_tables"),
                datasources=ctx.get("datasources"),
                datasource_ids=[ds.id for ds in ctx.get("datasources", [])],
            )
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            yield {"type": "error", "content": f"Execution error: {e}"}
            return

        if result.get("status") == "error":
            yield {"type": "error", "content": result.get("error", "Unknown SQL error")}
            return

        yield {
            "type": "data",
            "content": {
                "columns": result.get("columns", []),
                "rows": result.get("rows", []),
                "row_count": result.get("row_count", 0),
            },
        }

        if viz_requested:
            yield {"type": "thinking", "content": "Designing visualization..."}
            try:
                chart_option = await self._generate_chart(base_prompt, ctx, result)
                yield {"type": "chart", "content": chart_option}
            except Exception as e:
                logger.warning(f"Chart generation failed: {e}")

        row_count = result.get("row_count", 0)
        cols = result.get("columns", [])
        yield {
            "type": "answer",
            "content": f"Query returned {row_count} row(s) across {len(cols)} column(s).",
        }

    # -- keep for backward compat with BaseAgent contract --
    async def execute(self, query, context=None):
        from app.communication.info_unit import InformationUnit
        import time, uuid

        final_msg = ""
        async for step in self.stream_query(query, context):
            if step["type"] == "answer":
                final_msg = step["content"]
            elif step["type"] == "error":
                final_msg = step["content"]

        return InformationUnit(
            id=str(uuid.uuid4()),
            data_source="",
            role=self.agent_role,
            action="chat_bi_response",
            description=f"ChatBI: {query[:60]}",
            content={"message": final_msg},
            timestamp=time.time(),
        )

    # ---- internal helpers ----

    async def _generate_sql_stream(
        self, query: str, ctx: dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        prompt = self._render_prompt(
            "sql_generation.j2",
            query=query,
            schema=ctx.get("schema", ""),
            knowledge=ctx.get("knowledge", ""),
            dsl=ctx.get("dsl", ""),
        )
        messages = [self._system_message(), {"role": "user", "content": prompt}]
        async for chunk in llm_client.stream(messages, log_meta={"feature": "chat"}):
            yield chunk

    async def _generate_chart(
        self,
        query: str,
        ctx: dict[str, Any],
        sql_result: dict[str, Any],
    ) -> dict[str, Any]:
        preview_rows = sql_result.get("rows", [])[:8]
        columns = sql_result.get("columns", [])
        data_info = f"Columns: {columns}. Rows: {sql_result.get('row_count', 0)}. Sample: {preview_rows}"

        prompt = self._render_prompt(
            "chart_generation.j2",
            query=query,
            data_info=data_info,
            dsl=ctx.get("dsl", ""),
        )
        messages = [self._system_message(), {"role": "user", "content": prompt}]
        try:
            return await self._call_llm_json(messages, log_meta={"feature": "chat"})
        except Exception:
            raw = await self._call_llm(messages, log_meta={"feature": "chat"})
            return json.loads(_strip_sql_fences(raw))


def _strip_sql_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines)
        if lines[-1].strip() == "```":
            end -= 1
        text = "\n".join(lines[start:end]).strip()
    return text


chatbi_agent = ChatBIAgent()
