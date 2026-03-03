"""Cleaning Agent - Generates data cleaning and preparation code."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.communication.info_unit import InformationUnit

logger = logging.getLogger(__name__)

CLEANING_PROMPT = """You are an expert data engineer specializing in data cleaning and preparation.

{data_info}

Generate Python code that cleans and prepares the data:
1. Handle missing values (impute or drop based on context)
2. Remove duplicates
3. Fix data types
4. Handle outliers if appropriate
5. Standardize text/categorical columns if needed
6. Create a cleaned DataFrame named `df_clean`
7. Print a summary of changes made

User request: {query}

Respond with ONLY Python code, no markdown fences."""


class CleaningAgent(BaseAgent):
    agent_name = "cleaning_agent"
    agent_role = "Cleaning Agent"

    async def execute(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> InformationUnit:
        ctx = context or {}
        data_info = ctx.get("data_info", "No data description available")
        data_source = ctx.get("data_source", "")

        prompt = CLEANING_PROMPT.format(data_info=data_info, query=query)
        messages = [self._system_message(), {"role": "user", "content": prompt}]
        code = await self._call_llm(messages)

        code = code.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1]) if len(lines) > 2 else code

        return self._create_info_unit(
            content=code,
            action="clean_data",
            description=f"Data cleaning for: {query[:80]}",
            data_source=data_source,
        )


cleaning_agent = CleaningAgent()
