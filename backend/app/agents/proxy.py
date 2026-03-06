"""Proxy Agent - Orchestrates conversational support."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.agents.chat_agent import chat_agent
from app.communication.info_unit import InformationUnit
from app.notebook_runtime import build_query_context, build_runtime_bundle

logger = logging.getLogger(__name__)


class ProxyAgent(BaseAgent):
    """Orchestrator agent that routes queries to the conversational chat agent."""

    agent_name = "proxy_agent"
    agent_role = "Proxy Agent"

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        task_id = str(uuid.uuid4())

        # Build context for the chat agent
        notebook_cells = ctx.get("notebook_cells", [])
        if notebook_cells:
            runtime_bundle = build_runtime_bundle(notebook_cells)
            query_context = build_query_context(
                runtime_bundle,
                query,
                focus_cell_id=ctx.get("cell_id"),
                task_type="general",
                limit=10,
            )
            ctx["relevant_cells"] = query_context["cells"]
            ctx["notebook_context"] = query_context["notebook_context"]
            ctx["table_context"] = query_context["table_context"]

        # Directly call the chat agent, bypassing orchestration
        try:
            result = await chat_agent.execute(query, ctx)
            summary_message = result.content if isinstance(result.content, str) else "I've processed your request."
        except Exception as e:
            logger.error(f"Chat execution failed: {e}")
            summary_message = f"I'm sorry, I encountered an error: {str(e)}"

        final_content = {
            "task_id": task_id,
            "plan": {"agents": ["chat_agent"], "reasoning": "Conversational-only mode enabled."},
            "message": summary_message,
            "results": [],  # No cells are created in chat-only mode
        }

        return self._create_info_unit(
            content=final_content,
            action="chat_only_response",
            description=f"Direct chat response for: {query[:80]}",
        )


proxy_agent = ProxyAgent()
