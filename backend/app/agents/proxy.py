"""Proxy Agent - Orchestrates multi-agent task execution via FSM-based plans."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.agents.chart_agent import chart_agent
from app.agents.cleaning_agent import cleaning_agent
from app.agents.eda_agent import eda_agent
from app.agents.insight_agent import insight_agent
from app.agents.python_agent import python_agent
from app.agents.report_agent import report_agent
from app.agents.sql_agent import sql_agent
from app.communication.info_unit import InformationUnit
from app.communication.protocol import CommunicationProtocol
from app.execution import sql_executor
from app.notebook_runtime import build_query_context, build_runtime_bundle

logger = logging.getLogger(__name__)

AGENT_REGISTRY: dict[str, BaseAgent] = {
    "sql_agent": sql_agent,
    "python_agent": python_agent,
    "chart_agent": chart_agent,
    "insight_agent": insight_agent,
    "eda_agent": eda_agent,
    "cleaning_agent": cleaning_agent,
    "report_agent": report_agent,
}


class ProxyAgent(BaseAgent):
    """Orchestrator agent that routes queries and manages multi-agent execution."""

    agent_name = "proxy_agent"
    agent_role = "Proxy Agent"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.protocol = CommunicationProtocol()

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        task_id = str(uuid.uuid4())

        plan = await self._create_execution_plan(query, ctx)
        logger.info(f"Execution plan: {plan}")

        agents_list = plan.get("agents", ["sql_agent"])
        execution_steps = plan.get("execution_plan", [])

        if not execution_steps:
            execution_steps = [
                {"agent": a, "depends_on": [], "description": f"Execute {a}"}
                for a in agents_list
            ]

        runtime_bundle = None
        notebook_cells = ctx.get("notebook_cells", [])
        task_type = self._infer_task_type(agents_list, query)
        if notebook_cells:
            runtime_bundle = build_runtime_bundle(notebook_cells)
            query_context = build_query_context(
                runtime_bundle,
                query,
                focus_cell_id=ctx.get("cell_id"),
                task_type=task_type,
                limit=10,
            )
            ctx["relevant_cells"] = query_context["cells"]
            ctx["notebook_context"] = query_context["notebook_context"]
            ctx["table_context"] = query_context["table_context"]

        self.protocol.reset()
        self.protocol.setup_plan(execution_steps)

        results: list[InformationUnit] = []
        while not self.protocol.is_complete():
            ready_agents = self.protocol.get_next_agents()
            if not ready_agents:
                break

            for agent_name in ready_agents:
                agent = AGENT_REGISTRY.get(agent_name)
                if not agent:
                    logger.warning(f"Unknown agent: {agent_name}, skipping")
                    self.protocol.finish_agent(agent_name)
                    continue

                self.protocol.start_agent(agent_name)
                step_context = self._compose_step_context(ctx, agent_name)

                try:
                    result = await agent.execute(query, step_context)
                    materialized = self._materialize_result(result, ctx)
                    self.protocol.store_result(materialized)
                    results.append(materialized)
                except Exception as e:
                    logger.error(f"Agent {agent_name} failed: {e}")
                finally:
                    self.protocol.finish_agent(agent_name)

        final_content = {
            "task_id": task_id,
            "plan": plan,
            "results": [
                {
                    "agent": r.role,
                    "action": r.action,
                    "content": r.content,
                    "output": self._extract_cell_output(r),
                    "cell_type": self._infer_cell_type(r.role),
                }
                for r in results
            ],
        }

        return self._create_info_unit(
            content=final_content,
            action="orchestrate_agents",
            description=f"Completed multi-agent task for: {query[:80]}",
        )

    async def _create_execution_plan(
        self, query: str, context: dict[str, Any]
    ) -> dict:
        prompt = self._render_prompt(
            "task_routing.j2",
            query=query,
            context=str(context.get("notebook_context", "")),
        )
        messages = [self._system_message(), {"role": "user", "content": prompt}]

        try:
            return await self._call_llm_json(messages)
        except Exception as e:
            logger.warning(f"Plan generation failed, using default: {e}")
            return self._default_plan(query)

    def _default_plan(self, query: str) -> dict:
        query_lower = query.lower()
        if any(w in query_lower for w in ["chart", "plot", "graph", "visualiz", "show me"]):
            return {
                "agents": ["sql_agent", "chart_agent"],
                "execution_plan": [
                    {"agent": "sql_agent", "depends_on": [], "description": "Get data"},
                    {
                        "agent": "chart_agent",
                        "depends_on": ["sql_agent"],
                        "description": "Create visualization",
                    },
                ],
            }
        elif any(w in query_lower for w in ["clean", "fix", "missing", "duplicat"]):
            return {
                "agents": ["cleaning_agent"],
                "execution_plan": [
                    {"agent": "cleaning_agent", "depends_on": [], "description": "Clean data"},
                ],
            }
        elif any(w in query_lower for w in ["insight", "analyz", "pattern", "trend"]):
            return {
                "agents": ["sql_agent", "insight_agent"],
                "execution_plan": [
                    {"agent": "sql_agent", "depends_on": [], "description": "Get data"},
                    {
                        "agent": "insight_agent",
                        "depends_on": ["sql_agent"],
                        "description": "Analyze",
                    },
                ],
            }
        elif any(w in query_lower for w in ["report", "summary", "overview"]):
            return {
                "agents": ["sql_agent", "insight_agent", "report_agent"],
                "execution_plan": [
                    {"agent": "sql_agent", "depends_on": [], "description": "Get data"},
                    {
                        "agent": "insight_agent",
                        "depends_on": ["sql_agent"],
                        "description": "Analyze",
                    },
                    {
                        "agent": "report_agent",
                        "depends_on": ["insight_agent"],
                        "description": "Report",
                    },
                ],
            }
        elif any(w in query_lower for w in ["eda", "explor", "describe", "profile"]):
            return {
                "agents": ["eda_agent"],
                "execution_plan": [
                    {"agent": "eda_agent", "depends_on": [], "description": "EDA"},
                ],
            }
        elif any(w in query_lower for w in ["python", "code", "script", "compute", "calculat"]):
            return {
                "agents": ["python_agent"],
                "execution_plan": [
                    {
                        "agent": "python_agent",
                        "depends_on": [],
                        "description": "Generate code",
                    },
                ],
            }
        else:
            return {
                "agents": ["sql_agent"],
                "execution_plan": [
                    {"agent": "sql_agent", "depends_on": [], "description": "Query data"},
                ],
            }

    def _compose_step_context(
        self,
        base_context: dict[str, Any],
        agent_name: str,
    ) -> dict[str, Any]:
        predecessor_info = self.protocol.prepare_context(agent_name)
        step_context = {**base_context, "predecessor_info": predecessor_info}

        analysis_parts: list[str] = []
        data_parts: list[str] = []
        if base_context.get("table_context"):
            data_parts.append(str(base_context["table_context"]))
        if base_context.get("notebook_context"):
            analysis_parts.append(str(base_context["notebook_context"]))

        for info in predecessor_info:
            analysis_parts.append(info.to_context_string())
            if info.role == "SQL Agent":
                if isinstance(info.content, dict):
                    step_context["sql_query"] = info.content.get("query", "")
                    sql_result = info.content.get("result")
                    if isinstance(sql_result, dict):
                        preview = self._format_sql_result(sql_result)
                        if preview:
                            data_parts.append(preview)
                            analysis_parts.append(preview)
                else:
                    step_context["sql_query"] = str(info.content)
            elif info.role in {"Insight Agent", "Report Agent"}:
                analysis_parts.append(str(info.content))

        step_context["data_info"] = "\n\n".join(part for part in data_parts if part)
        step_context["analysis_context"] = "\n\n".join(part for part in analysis_parts if part)
        return step_context

    def _materialize_result(
        self,
        result: InformationUnit,
        context: dict[str, Any],
    ) -> InformationUnit:
        if result.role == "SQL Agent" and isinstance(result.content, str):
            preview = sql_executor.execute(result.content, context.get("datasource_id"))
            result.content = {
                "query": result.content,
                "result": preview,
            }
        return result

    @staticmethod
    def _extract_cell_output(result: InformationUnit) -> dict[str, Any] | None:
        if result.role == "SQL Agent" and isinstance(result.content, dict):
            output = result.content.get("result")
            if isinstance(output, dict):
                return output
        return None

    @staticmethod
    def _format_sql_result(result: dict[str, Any]) -> str:
        columns = result.get("columns") or []
        row_count = result.get("row_count", 0)
        if not columns:
            return ""
        preview_rows = result.get("rows", [])[:5]
        return (
            f"SQL result with columns {columns} and {row_count} rows. "
            f"Preview rows: {preview_rows}"
        )

    @staticmethod
    def _infer_task_type(agents_list: list[str], query: str) -> str:
        if "chart_agent" in agents_list:
            return "nl2vis"
        if "report_agent" in agents_list:
            return "report"
        if "insight_agent" in agents_list:
            return "nl2insight"
        if "eda_agent" in agents_list:
            return "eda"
        if "cleaning_agent" in agents_list:
            return "cleaning"
        if "python_agent" in agents_list:
            return "nl2dscode"
        if "sql_agent" in agents_list:
            return "nl2sql"
        if "chart" in query.lower():
            return "nl2vis"
        return "general"

    @staticmethod
    def _infer_cell_type(role: str) -> str:
        mapping = {
            "SQL Agent": "sql",
            "Python Agent": "python",
            "Chart Agent": "chart",
            "Insight Agent": "markdown",
            "EDA Agent": "python",
            "Cleaning Agent": "python",
            "Report Agent": "markdown",
        }
        return mapping.get(role, "python")


proxy_agent = ProxyAgent()
