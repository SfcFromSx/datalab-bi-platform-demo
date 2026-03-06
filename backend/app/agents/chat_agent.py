"""Chat Agent - Handles general conversation and educational support."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.communication.info_unit import InformationUnit

logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    agent_name = "chat_agent"
    agent_role = "Chat Agent"

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        notebook_context = ctx.get("notebook_context", "No context available")
        table_context = ctx.get("table_context", "{}")

        prompt = self._render_prompt(
            "chat_generation.j2",
            query=query,
            notebook_context=notebook_context,
            table_context=table_context,
        )

        messages = [self._system_message(), {"role": "user", "content": prompt}]
        response = await self._call_llm(messages, temperature=0.7)

        logger.info(f"ChatAgent response generated for query: {query[:50]}...")

        return self._create_info_unit(
            content=response,
            action="chat_response",
            description=f"Generated conversational response for: {query[:80]}",
        )


chat_agent = ChatAgent()
