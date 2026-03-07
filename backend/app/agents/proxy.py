"""Proxy Agent - Orchestrates conversational support."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.agents.chat_agent import chat_agent
from app.communication.info_unit import InformationUnit

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
        task_id = str(uuid.uuid4())

        # Directly call the chat agent
        try:
            result = await chat_agent.execute(query, context)
            if isinstance(result.content, str):
                summary_message = result.content
            elif isinstance(result.content, dict) and "message" in result.content:
                summary_message = str(result.content["message"])
            else:
                summary_message = "I've processed your request."
        except Exception as e:
            logger.error(f"Chat execution failed: {e}")
            summary_message = f"I'm sorry, I encountered an error: {str(e)}"

        final_content = {
            "task_id": task_id,
            "message": summary_message,
        }

        return self._create_info_unit(
            content=final_content,
            action="chat_only_response",
            description=f"Direct chat response for: {query[:80]}",
        )


proxy_agent = ProxyAgent()
