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
from app.communication.fsm import AgentFSM, FSMState
from app.communication.info_unit import InformationUnit
from app.communication.shared_buffer import SharedBuffer

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
        self.buffer = SharedBuffer()

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

        fsm = AgentFSM()
        for step in execution_steps:
            fsm.add_state(step["agent"], FSMState.WAIT)
            for dep in step.get("depends_on", []):
                fsm.add_transition(dep, step["agent"])

        results: list[InformationUnit] = []

        for step in execution_steps:
            agent_name = step["agent"]
            agent = AGENT_REGISTRY.get(agent_name)
            if not agent:
                logger.warning(f"Unknown agent: {agent_name}, skipping")
                continue

            fsm.transition(agent_name, FSMState.EXECUTION)

            predecessor_info = self.buffer.retrieve_for_agent(
                agent_name, fsm.get_predecessors(agent_name)
            )
            step_context = {**ctx}
            if predecessor_info:
                step_context["predecessor_info"] = predecessor_info
                for info in predecessor_info:
                    if info.role == "SQL Agent" and isinstance(info.content, str):
                        step_context["sql_result"] = info.content
                    elif info.role == "Python Agent" and isinstance(info.content, str):
                        step_context["python_result"] = info.content

            try:
                result = await agent.execute(query, step_context)
                self.buffer.store(result)
                results.append(result)
                fsm.transition(agent_name, FSMState.FINISH)
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                fsm.transition(agent_name, FSMState.FINISH)

        final_content = {
            "task_id": task_id,
            "plan": plan,
            "results": [
                {
                    "agent": r.role,
                    "action": r.action,
                    "content": r.content,
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
