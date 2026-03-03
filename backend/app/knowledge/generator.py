"""Knowledge Generation using Map-Reduce with self-calibration.

Implements Algorithm 1 from the DataLab paper:
- Map Phase: Extract knowledge from each historical script
- Self-Calibration: Score and regenerate if below threshold
- Reduce Phase: Synthesize knowledge across all scripts
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.llm.client import LLMClient, llm_client

logger = logging.getLogger(__name__)

CALIBRATION_PROMPT = """Score the following knowledge extraction on a scale of 1-5.

Consider:
- Correctness: Are the descriptions accurate based on the script?
- Comprehensiveness: Are all relevant tables/columns covered?
- Clarity: Are descriptions clear and useful?
- Specificity: Do descriptions capture business-specific meaning?

Knowledge:
{knowledge}

Original Script:
{script}

Respond with a JSON object: {{"score": 3, "feedback": "brief feedback"}}"""


class MapReduceKnowledgeGenerator:
    """Generate domain knowledge from data processing scripts using LLMs."""

    def __init__(self, llm: Optional[LLMClient] = None, score_threshold: float = 3.0):
        self.llm = llm or llm_client
        self.score_threshold = score_threshold

    async def generate(
        self,
        schema: str,
        scripts: list[str],
        lineage: str = "",
    ) -> dict[str, Any]:
        scripts = self._preprocess_scripts(scripts)

        map_results = []
        for script in scripts:
            knowledge = await self._map_phase(schema, script, lineage)
            map_results.append(knowledge)

        final_knowledge = await self._reduce_phase(map_results, schema, lineage)
        return final_knowledge

    def _preprocess_scripts(self, scripts: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for script in scripts:
            normalized = script.strip().lower()
            if normalized not in seen and len(normalized) > 20:
                seen.add(normalized)
                unique.append(script)
        return unique[:20]

    async def _map_phase(
        self, schema: str, script: str, lineage: str
    ) -> dict[str, Any]:
        from app.agents.base import _jinja_env

        template = _jinja_env.get_template("knowledge_extraction.j2")
        prompt = template.render(schema=schema, script=script, lineage=lineage or None)

        messages = [
            {"role": "system", "content": "You are a domain knowledge extraction expert."},
            {"role": "user", "content": prompt},
        ]

        knowledge: dict[str, Any] = {}
        max_attempts = 3
        for attempt in range(max_attempts):
            knowledge = await self.llm.complete_json(messages)
            score = await self._self_calibrate(knowledge, script)

            if score >= self.score_threshold:
                return knowledge

            logger.info(
                f"Knowledge score {score} < {self.score_threshold}, "
                f"regenerating (attempt {attempt + 2})"
            )

        return knowledge

    async def _self_calibrate(self, knowledge: dict, script: str) -> float:
        prompt = CALIBRATION_PROMPT.format(
            knowledge=json.dumps(knowledge, indent=2, default=str),
            script=script[:2000],
        )

        messages = [
            {"role": "system", "content": "You are a knowledge quality evaluator."},
            {"role": "user", "content": prompt},
        ]

        try:
            result = await self.llm.complete_json(messages)
            return float(result.get("score", 3.0))
        except Exception:
            return 3.0

    async def _reduce_phase(
        self,
        map_results: list[dict[str, Any]],
        schema: str,
        lineage: str,
    ) -> dict[str, Any]:
        if not map_results:
            return {"database": {}, "table": {}, "columns": {}}

        if len(map_results) == 1:
            return map_results[0]

        results_text = json.dumps(map_results, indent=2, default=str)
        if len(results_text) > 12000:
            results_text = results_text[:12000] + "\n... (truncated)"

        prompt = f"""Synthesize the following knowledge extractions from multiple scripts into
a single, comprehensive, conflict-free knowledge set.

## Schema
{schema}

## Individual Knowledge Extractions
{results_text}

Merge descriptions, combine usage patterns, resolve conflicts.
Respond with a single JSON object:
{{"database": {{}}, "table": {{}}, "columns": {{}}}}"""

        messages = [
            {"role": "system", "content": "You are a knowledge synthesis expert."},
            {"role": "user", "content": prompt},
        ]

        try:
            return await self.llm.complete_json(messages)
        except Exception as e:
            logger.error(f"Reduce phase failed: {e}")
            return map_results[0] if map_results else {"database": {}, "table": {}, "columns": {}}


knowledge_generator = MapReduceKnowledgeGenerator()
