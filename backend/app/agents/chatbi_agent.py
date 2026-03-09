"""ChatBI Agent - Focused on Natural Language to SQL and Charts."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional, AsyncGenerator

from app.agents.base import BaseAgent
from app.communication.info_unit import InformationUnit
from app.execution import sql_executor
from app.llm.client import llm_client

logger = logging.getLogger(__name__)


class ChatBIAgent(BaseAgent):
    """Unified agent that handles SQL and Chart generation directly from natural language."""

    agent_name = "chat_bi_agent"
    agent_role = "Chat BI Agent"

    async def execute_stream(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[str | dict[str, Any], None]:
        ctx = context or {}
        
        yield "> Thinking: Analyzing data request...\n\n"
        # 1. Determine if visualization is requested
        viz_requested = any(w in query.lower() for w in ["chart", "plot", "graph", "visualize", "show me a", "draw"])
        
        # 2. Add Notebook Context for NL2SQL
        base_prompt = query
        nb_context = ctx.get("notebook_context")
        if nb_context:
            base_prompt += f"\n\nHere is some context from the current notebook:\n{nb_context}"

        sections = [
            {"id": "analyzing", "title": "Analyzing Request", "content": "Analyzing data request...", "status": "running", "type": "markdown"}
        ]
        yield {
            "message": "> Thinking: Analyzing data request...\n\n",
            "sections": sections
        }
        
        # 1. Plan
        # (This is fast, we just mark it done)
        sections[0]["status"] = "done"
        sections[0]["content"] = "Data request analyzed."

        # 2. SQL generation setup
        sections.append({"id": "sql_gen", "title": "Generating SQL", "content": "", "status": "running", "type": "sql"})
        
        sql_query = ""
        try:
            async for chunk in self._generate_sql_stream(base_prompt, ctx):
                sql_query += chunk
                display_sql = sql_query.strip()
                if display_sql.startswith("```"):
                     lines = display_sql.split("\n")
                     if len(lines) > 1:
                         display_sql = "\n".join(lines[1:])
                
                sections[1]["content"] = display_sql
                yield {
                    "message": f"> Thinking: Generating SQL...\n\n```sql\n{display_sql}\n```",
                    "sections": sections,
                    "status": "running"
                }
            
            # Final clean up of SQL
            sql_query = sql_query.strip()
            if sql_query.startswith("```"):
                lines = sql_query.split("\n")
                if len(lines) > 2:
                    sql_query = "\n".join(lines[1:-1])
                else:
                    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            
            sections[1]["status"] = "done"
            sections[1]["content"] = sql_query

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            sections[1]["status"] = "error"
            sections[1]["content"] = str(e)
            yield {
                "message": f"I'm sorry, I couldn't generate the SQL for your request: {e}",
                "sections": sections,
                "status": "error"
            }
            return

        # 3. Execution
        sections.append({"id": "execution", "title": "Executing SQL", "content": "Running query on DuckDB...", "status": "running", "type": "markdown"})
        yield {
            "message": f"> Thinking: Generating SQL...\n\n```sql\n{sql_query}\n```\n\n> Thinking: Executing SQL...\n\n",
            "sections": sections,
            "status": "running"
        }
        
        try:
            # Use isolated execution to match SQL cell behavior
            query_result = sql_executor.execute_isolated(
                sql_query,
                tables=ctx.get("raw_tables"),
                datasources=ctx.get("datasources"),
                datasource_ids=[ds.id for ds in ctx.get("datasources", [])]
            )
            
            if query_result.get("status") == "error":
                error_msg = query_result.get("error", "Unknown error")
                sections[2]["status"] = "error"
                sections[2]["content"] = error_msg
                yield {
                    "message": f"**Error executing SQL:** {error_msg}",
                    "sections": sections,
                    "status": "error"
                }
                return

            sections[2]["status"] = "done"
            sections[2]["content"] = "Query executed successfully."

            table_data = {
                "columns": query_result.get("columns", []),
                "rows": query_result.get("rows", [])
            }
            
            # 4. Results
            markdown_table = self._format_markdown_table(query_result)
            current_message = markdown_table
            
            yield {
                "message": current_message,
                "data": table_data,
                "sections": sections
            }

            # 5. Optional Chart Generation
            if viz_requested:
                sections.append({"id": "chart_gen", "title": "Designing Chart", "content": "Designing visualization...", "status": "running", "type": "markdown"})
                yield {
                    "message": current_message,
                    "data": table_data,
                    "sections": sections
                }
                
                preview_str = self._format_sql_result(query_result)
                ctx["data_info"] = preview_str if preview_str else "No preview available"
                
                chart_spec = await self._generate_chart(base_prompt, ctx)
                
                try:
                    chart_json = json.loads(chart_spec) if isinstance(chart_spec, str) else chart_spec
                except:
                    chart_json = {"error": "Invalid chart specification"}

                sections[3]["status"] = "done"
                sections[3]["content"] = "Chart designed."

                yield {
                    "message": current_message,
                    "data": table_data,
                    "chart": chart_json,
                    "sections": sections
                }

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            yield {
                "message": f"\n\nAn unexpected error occurred: {str(e)}",
                "sections": sections,
                "status": "error"
            }

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        """Fallback synchronous execution for the ChatBI agent."""
        ctx = context or {}
        task_id = str(uuid.uuid4())
        
        # Determine intent (simplified)
        viz_requested = any(w in query.lower() for w in ["chart", "plot", "graph", "visualize"])
        
        base_prompt = query
        nb_context = ctx.get("notebook_context")
        if nb_context:
            base_prompt += f"\n\nContext:\n{nb_context}"

        try:
            # 1. Generate SQL
            sql_query = await self._generate_sql(base_prompt, ctx)
            
            # 2. Execute using isolated flow for context awareness
            query_result = sql_executor.execute_isolated(
                sql_query,
                tables=ctx.get("raw_tables"),
                datasources=ctx.get("datasources"),
                datasource_ids=[ds.id for ds in ctx.get("datasources", [])]
            )
            
            if query_result.get("status") == "error":
                error_msg = query_result.get("error", "Unknown execution error")
                summary_message = f"SQL failed:\n\n```sql\n{sql_query}\n```\n\nError: {error_msg}"
            else:
                markdown_table = self._format_markdown_table(query_result)
                summary_message = f"Results for: {query}\n\n```sql\n{sql_query}\n```\n\n{markdown_table}"
                
                # 3. Optional Chart
                if viz_requested:
                    preview_str = self._format_sql_result(query_result)
                    ctx["data_info"] = preview_str if preview_str else "No preview available"
                    chart_spec = await self._generate_chart(base_prompt, ctx)
                    summary_message += f"\n\n```json\n{chart_spec}\n```"

        except Exception as e:
            logger.error(f"ChatBI Sync Execution failed: {e}")
            summary_message = f"Error: {str(e)}"

        return self._create_info_unit(
            content={"task_id": task_id, "message": summary_message, "results": []},
            action="chat_bi_response",
            description=f"ChatBI response for: {query[:50]}",
        )

    async def _generate_sql(self, query: str, ctx: dict[str, Any]) -> str:
        sql = ""
        async for chunk in self._generate_sql_stream(query, ctx):
            sql += chunk
        
        sql = sql.strip()
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1]) if len(lines) > 2 else sql
        return sql

    async def _generate_sql_stream(self, query: str, ctx: dict[str, Any]) -> AsyncGenerator[str, None]:
        schema = ctx.get("schema", "No schema available")
        knowledge = ctx.get("knowledge", "")
        dsl = ctx.get("dsl", "")

        prompt = self._render_prompt(
            "sql_generation.j2",
            query=query,
            schema=schema,
            knowledge=knowledge,
            dsl=dsl,
        )

        messages = [self._system_message(), {"role": "user", "content": prompt}]
        async for chunk in llm_client.stream(messages):
            yield chunk

    async def _generate_chart(self, query: str, ctx: dict[str, Any]) -> str:
        data_info = ctx.get("data_info", "")
        dsl = ctx.get("dsl", "")

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

        return json.dumps(chart_spec, indent=2)

    @staticmethod
    def _format_sql_result(result: dict[str, Any]) -> str:
        columns = result.get("columns") or []
        row_count = result.get("row_count", 0)
        if not columns:
            return ""
        preview_rows = result.get("rows", [])[:5]
        return (
            f"Columns: {columns}. Total Rows: {row_count}. "
            f"Sample Data: {preview_rows}"
        )

    @staticmethod
    def _format_markdown_table(result: dict[str, Any]) -> str:
        columns = result.get("columns") or []
        if not columns:
            return "No data returned."
        
        rows = result.get("rows", [])
        
        # Header
        md = "| " + " | ".join(map(str, columns)) + " |\n"
        md += "| " + " | ".join(["---"] * len(columns)) + " |\n"
        
        # Rows
        for row in rows:
            md += "| " + " | ".join(map(str, row)) + " |\n"
            
        return md


chatbi_agent = ChatBIAgent()
