"""Base agent class for all DataLab agents."""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from app.communication.info_unit import InformationUnit
from app.config import settings
from app.llm.client import LLMClient, llm_client

logger = logging.getLogger(__name__)

_jinja_env = Environment(
    loader=FileSystemLoader(str(settings.prompts_dir)),
    autoescape=False,
)


class BaseAgent(ABC):
    """Abstract base class for all DataLab agents.

    Each agent can:
    - Render prompt templates with context
    - Call the LLM for completions
    - Parse structured output
    - Create InformationUnits for inter-agent communication
    """

    agent_name: str = "base"
    agent_role: str = "Base Agent"
    max_retries: int = 3

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or llm_client

    @abstractmethod
    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        """Execute the agent's primary task and return an InformationUnit."""
        ...

    def _render_prompt(self, template_name: str, **kwargs: Any) -> str:
        template = _jinja_env.get_template(template_name)
        return template.render(**kwargs)

    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        for attempt in range(self.max_retries):
            try:
                return await self.llm.complete(
                    messages, temperature=temperature, max_tokens=max_tokens
                )
            except Exception as e:
                logger.warning(f"{self.agent_role} LLM call attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
        return ""

    async def _call_llm_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> dict:
        for attempt in range(self.max_retries):
            try:
                return await self.llm.complete_json(messages, temperature=temperature)
            except Exception as e:
                logger.warning(
                    f"{self.agent_role} JSON LLM call attempt {attempt + 1} failed: {e}"
                )
                if attempt == self.max_retries - 1:
                    raise
        return {}

    def _create_info_unit(
        self,
        content: Any,
        action: str,
        description: str,
        data_source: str = "",
        cell_id: Optional[str] = None,
    ) -> InformationUnit:
        return InformationUnit(
            id=str(uuid.uuid4()),
            data_source=data_source,
            role=self.agent_role,
            action=action,
            description=description,
            content=content,
            timestamp=time.time(),
            cell_id=cell_id,
        )

    def _system_message(self) -> dict[str, str]:
        system_prompt = self._render_prompt("system.j2")
        return {"role": "system", "content": system_prompt}
