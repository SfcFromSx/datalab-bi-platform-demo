"""Chat Agent - Handles general conversation and educational support."""

from __future__ import annotations

import json
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
        prompt = self._render_prompt(
            "chat_generation.j2",
            query=query,
        )
        prompt = self._attach_context(prompt, ctx)

        messages = [self._system_message(), {"role": "user", "content": prompt}]
        response = await self._call_llm(messages, temperature=0.7)

        logger.info(f"ChatAgent response generated for query: {query[:50]}...")

        return self._create_info_unit(
            content=response,
            action="chat_response",
            description=f"Generated conversational response for: {query[:80]}",
        )

    @staticmethod
    def _attach_context(prompt: str, context: dict[str, Any]) -> str:
        sections: list[str] = []

        notebook_context = context.get("notebook_context")
        if notebook_context:
            sections.append(f"Notebook context:\n{notebook_context}")

        table_context = context.get("table_context")
        if isinstance(table_context, str) and table_context not in {"", "{}"}:
            sections.append(f"Available tables:\n{table_context}")

        value_context = context.get("value_context")
        if isinstance(value_context, str) and value_context not in {"", "{}"}:
            sections.append(f"Available scalar values:\n{value_context}")

        datasource_context = context.get("datasource_context")
        if datasource_context:
            sections.append(f"Datasource context:\n{datasource_context}")

        cell_context = context.get("cell_context")
        if cell_context:
            sections.append(
                "Focused cell neighborhood:\n"
                f"{json.dumps(cell_context, default=str, indent=2)}"
            )

        available_bindings = context.get("available_bindings")
        if available_bindings:
            sections.append(f"Notebook bindings: {', '.join(available_bindings)}")

        if not sections:
            return prompt

        sections.append(
            "Use notebook context when it helps. If the notebook state is incomplete, "
            "say that directly instead of inventing details."
        )
        return "\n\n".join([prompt, *sections])


chat_agent = ChatAgent()
