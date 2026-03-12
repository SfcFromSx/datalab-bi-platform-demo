"""Design Agent - Translates natural language instructions into notebook cell operations."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

from app.agents.base import BaseAgent
from app.llm.client import llm_client

logger = logging.getLogger(__name__)

_DESIGN_SYSTEM_PROMPT = """You are a notebook design assistant. Your job is to translate the user's natural-language instructions into a list of notebook cell operations.

You MUST respond with a valid JSON array of operations. Each operation is a JSON object with:
- "action": one of "add_cell", "edit_cell", "delete_cell", "move_cell", "execute_cell"
- "description": a short human-readable description of what this operation does

For "add_cell":
  - "cell_type": one of "sql", "python", "chart", "markdown"
  - "source": the cell source code/content
  - "position": (optional) integer position in the notebook

For "edit_cell":
  - "cell_id": the ID of the cell to edit
  - "source": the new source code

For "delete_cell":
  - "cell_id": the ID of the cell to delete

For "move_cell":
  - "cell_id": the ID of the cell to move
  - "position": the new position

For "execute_cell":
  - "cell_id": the ID of the cell to execute

RULES:
1. Return ONLY a JSON array. No markdown fences, no explanations outside JSON.
2. Each operation should be self-contained and actionable.
3. When the user asks for a new cell, use "add_cell" with appropriate content.
4. When editing, reference the cell_id from the notebook context.
5. If unsure which cell to edit, prefer creating a new one.
6. Generate complete, working source code for cells."""


class DesignAgent(BaseAgent):
    agent_name = "design_agent"
    agent_role = "Design Agent"

    async def stream_design(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        ctx = context or {}
        yield {"type": "thinking", "content": "Understanding your design request..."}

        notebook_context = ctx.get("notebook_context", "")
        cells_summary = ctx.get("cells_summary", "")
        table_context = ctx.get("table_context", "{}")

        user_prompt = "\n\n".join(filter(None, [
            f"User request: {query}",
            f"Current notebook cells:\n{cells_summary}" if cells_summary else None,
            f"Notebook context:\n{notebook_context}" if notebook_context else None,
            f"Available tables:\n{table_context}" if table_context != "{}" else None,
        ]))

        messages = [
            {"role": "system", "content": _DESIGN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = await self._call_llm_json(messages)
        except Exception:
            raw = await self._call_llm(messages)
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                start = 1
                end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                raw = "\n".join(lines[start:end]).strip()
            result = json.loads(raw)

        actions = result if isinstance(result, list) else [result]

        for action in actions:
            if not isinstance(action, dict) or "action" not in action:
                continue
            yield {"type": "action", "content": action}

        desc_parts = []
        for a in actions:
            desc = a.get("description", a.get("action", "operation"))
            desc_parts.append(f"- {desc}")
        summary = f"Completed {len(actions)} operation(s):\n" + "\n".join(desc_parts)
        yield {"type": "answer", "content": summary}

    async def execute(self, query, context=None):
        from app.communication.info_unit import InformationUnit
        import time, uuid

        final_msg = ""
        async for step in self.stream_design(query, context):
            if step["type"] == "answer":
                final_msg = step["content"]

        return InformationUnit(
            id=str(uuid.uuid4()),
            data_source="",
            role=self.agent_role,
            action="design_response",
            description=f"Design: {query[:60]}",
            content={"message": final_msg},
            timestamp=time.time(),
        )


design_agent = DesignAgent()
