"""Auto Analysis Agent - Autonomous multi-step data analysis."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.execution import sql_executor
from app.execution.cell_runtime import CellRuntime
from app.models import Cell, DataSource, Notebook
from app.models.agent_task import AgentTask, AgentTaskStatus
from app.models.cell import CellType

logger = logging.getLogger(__name__)

_PLAN_SYSTEM_PROMPT = """You are an autonomous data analysis agent. Given a user query and available data context, create an analysis plan.

Respond with a JSON object:
{
  "plan": [
    {"index": 0, "description": "Step description", "cell_type": "sql", "source": "SQL or code here"},
    ...
  ],
  "summary_prompt": "What the final summary should cover"
}

RULES:
1. Each step creates a notebook cell. Use "sql" for data queries, "python" for computation, "chart" for visualization, "markdown" for narrative.
2. Steps execute in order. Later SQL cells can reference outputs from earlier cells using the -- output: variable_name comment.
3. Keep plans focused: 2-6 steps is typical. Don't over-engineer.
4. For SQL cells, always include an `-- output: variable_name` comment on the first line so downstream cells can reference it.
5. Generate complete, working source code for each step.
6. Return ONLY valid JSON, no markdown fences or extra text."""

_SUMMARY_SYSTEM_PROMPT = """You are a data analyst. Summarize the analysis results clearly and concisely in markdown.
Focus on key findings, trends, and actionable insights. Be specific with numbers from the data."""

cell_runtime = CellRuntime()


class AutoAnalysisAgent(BaseAgent):
    agent_name = "auto_analysis_agent"
    agent_role = "Auto Analysis Agent"

    async def run_task(
        self,
        task: AgentTask,
        session: AsyncSession,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run a full autonomous analysis, yielding SSE step dicts."""
        task.status = AgentTaskStatus.RUNNING.value
        await session.flush()

        yield {"type": "thinking", "content": "Planning analysis approach..."}

        context = await self._build_context(task, session)

        try:
            plan_data = await self._generate_plan(task.query, context)
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            task.status = AgentTaskStatus.FAILED.value
            task.error = str(e)
            await session.flush()
            yield {"type": "error", "content": f"Failed to generate plan: {e}"}
            return

        plan_steps = plan_data.get("plan", [])
        summary_prompt = plan_data.get("summary_prompt", "Summarize the analysis results.")

        task.plan = [
            {"index": s["index"], "description": s["description"], "status": "pending"}
            for s in plan_steps
        ]
        task.progress = 0.1
        await session.flush()

        yield {
            "type": "plan",
            "content": task.plan,
        }

        total = len(plan_steps)
        results_context: list[str] = []

        for i, step in enumerate(plan_steps):
            step_progress = 0.1 + (0.8 * i / max(total, 1))
            task.progress = step_progress
            task.plan[i]["status"] = "running"
            await session.flush()

            yield {
                "type": "plan",
                "content": task.plan,
            }

            yield {
                "type": "agent_progress",
                "content": {
                    "progress": step_progress,
                    "message": f"Step {i + 1}/{total}: {step['description']}",
                    "step_index": i,
                },
            }

            cell_type = step.get("cell_type", "sql")
            source = step.get("source", "")

            try:
                cell = await self._create_and_execute_cell(
                    task, session, cell_type, source, i
                )
                task.plan[i]["status"] = "completed"
                task.plan[i]["cell_id"] = cell.id
                task.cells_created += 1
                if cell_type == "sql":
                    task.queries_executed += 1

                output = cell.output or {}
                if output.get("data"):
                    cols = output["data"].get("columns", [])
                    rows = output["data"].get("rows", [])
                    preview = rows[:5]
                    results_context.append(
                        f"Step {i + 1} ({step['description']}): "
                        f"columns={cols}, rows={len(rows)}, sample={preview}"
                    )
            except Exception as e:
                logger.error(f"Step {i} failed: {e}")
                task.plan[i]["status"] = "failed"
                results_context.append(f"Step {i + 1}: FAILED - {e}")

            await session.flush()

            yield {
                "type": "plan",
                "content": task.plan,
            }

        task.progress = 0.9
        await session.flush()

        yield {
            "type": "agent_progress",
            "content": {"progress": 0.9, "message": "Generating analysis summary..."},
        }

        try:
            summary = await self._generate_summary(
                task.query, summary_prompt, results_context
            )
        except Exception as e:
            summary = f"Analysis completed with {total} steps. Summary generation failed: {e}"

        if task.notebook_id:
            md_cell = Cell(
                notebook_id=task.notebook_id,
                cell_type=CellType.MARKDOWN,
                source=f"## Analysis Summary\n\n{summary}",
                position=1000 + total,
            )
            session.add(md_cell)
            await session.flush()
            task.cells_created += 1

        task.status = AgentTaskStatus.COMPLETED.value
        task.progress = 1.0
        task.result = {"summary": summary}
        await session.flush()

        yield {"type": "summary", "content": summary}

    async def _build_context(self, task: AgentTask, session: AsyncSession) -> dict:
        context: dict[str, Any] = {}
        if task.notebook_id:
            from app.agents.context_builder import load_notebook_query_context
            context = await load_notebook_query_context(
                session, task.notebook_id, task.query,
                datasource_id=task.datasource_id,
            )
        return context

    async def _generate_plan(self, query: str, context: dict) -> dict:
        notebook_context = context.get("notebook_context", "")
        table_context = context.get("table_context", "{}")

        user_prompt = "\n\n".join(filter(None, [
            f"Analysis request: {query}",
            f"Available data context:\n{notebook_context}" if notebook_context else None,
            f"Available tables:\n{table_context}" if table_context != "{}" else None,
        ]))

        messages = [
            {"role": "system", "content": _PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        return await self._call_llm_json(messages)

    async def _create_and_execute_cell(
        self,
        task: AgentTask,
        session: AsyncSession,
        cell_type: str,
        source: str,
        step_index: int,
    ) -> Cell:
        if not task.notebook_id:
            notebook = Notebook(title=f"Agent Analysis: {task.query[:50]}")
            session.add(notebook)
            await session.flush()
            task.notebook_id = notebook.id

        ct = CellType(cell_type) if cell_type in CellType.__members__.values() else CellType.SQL
        cell = Cell(
            notebook_id=task.notebook_id,
            cell_type=ct,
            source=source,
            position=1000 + step_index,
        )
        session.add(cell)
        await session.flush()

        notebook_cells_result = await session.execute(
            select(Cell)
            .where(Cell.notebook_id == task.notebook_id)
            .order_by(Cell.position)
        )
        notebook_cells = notebook_cells_result.scalars().all()

        ds_result = await session.execute(select(DataSource))
        datasources = ds_result.scalars().all()

        try:
            execution_result = await cell_runtime.execute_target(
                notebook_cells,
                cell.id,
                datasources=datasources,
            )
            output = execution_result.outputs_by_id.get(cell.id, {})
            cell.output = output
            for nc in notebook_cells:
                if nc.id in execution_result.outputs_by_id and nc.id != cell.id:
                    nc.output = execution_result.outputs_by_id[nc.id]
        except Exception as e:
            cell.output = {"status": "error", "error": str(e)}

        await session.flush()
        return cell

    async def _generate_summary(
        self, query: str, summary_prompt: str, results_context: list[str]
    ) -> str:
        user_prompt = "\n\n".join([
            f"Original question: {query}",
            f"Summary focus: {summary_prompt}",
            "Analysis results:\n" + "\n".join(results_context),
        ])
        messages = [
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        return await self._call_llm(messages)

    async def execute(self, query, context=None):
        from app.communication.info_unit import InformationUnit
        return InformationUnit(
            id=str(uuid.uuid4()),
            data_source="",
            role=self.agent_role,
            action="auto_analysis",
            description=f"Auto analysis: {query[:60]}",
            content={"message": "Use run_task() for full execution."},
            timestamp=time.time(),
        )


auto_agent = AutoAnalysisAgent()
