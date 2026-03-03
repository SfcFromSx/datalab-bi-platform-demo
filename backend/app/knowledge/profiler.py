"""Data Profiler - Fallback for tables without historical scripts.

Two stages:
1. Heuristics-based analysis (column types, stats, samples)
2. LLM-based interpretation (semantic descriptions)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.execution.sql_executor import sql_executor
from app.llm.client import LLMClient, llm_client

logger = logging.getLogger(__name__)


class DataProfiler:
    """Profile datasets to extract structural and semantic information."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or llm_client

    async def profile(
        self,
        table_name: str,
        datasource_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate a comprehensive profile for a table."""
        heuristic_profile = self._heuristic_analysis(table_name, datasource_id)
        semantic_profile = await self._llm_interpretation(heuristic_profile)

        return {
            "table_name": table_name,
            "heuristic": heuristic_profile,
            "semantic": semantic_profile,
        }

    def _heuristic_analysis(
        self, table_name: str, datasource_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Extract basic statistics and structure from the table."""
        schema = sql_executor.get_schema(table_name, datasource_id)

        count_result = sql_executor.execute(
            f'SELECT COUNT(*) as cnt FROM "{table_name}"', datasource_id
        )
        row_count = 0
        if count_result["rows"]:
            row_count = count_result["rows"][0][0]

        columns_info = []
        for col in schema:
            col_name = col["column_name"]
            col_type = col["column_type"]

            sample_result = sql_executor.execute(
                f'SELECT DISTINCT "{col_name}" FROM "{table_name}" LIMIT 10',
                datasource_id,
            )
            samples = [row[0] for row in sample_result.get("rows", [])]

            stats = {}
            if col_type.lower() in ("integer", "bigint", "float", "double", "decimal", "numeric"):
                stats_result = sql_executor.execute(
                    f'SELECT MIN("{col_name}"), MAX("{col_name}"), '
                    f'AVG("{col_name}") FROM "{table_name}"',
                    datasource_id,
                )
                if stats_result["rows"]:
                    row = stats_result["rows"][0]
                    stats = {"min": row[0], "max": row[1], "avg": row[2]}

            null_result = sql_executor.execute(
                f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NULL',
                datasource_id,
            )
            null_count = null_result["rows"][0][0] if null_result["rows"] else 0

            columns_info.append({
                "name": col_name,
                "type": col_type,
                "samples": [str(s) for s in samples],
                "null_count": null_count,
                "null_rate": null_count / max(row_count, 1),
                "stats": stats,
            })

        return {
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(schema),
            "columns": columns_info,
        }

    async def _llm_interpretation(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Use LLM to interpret the heuristic profile and generate descriptions."""
        import json

        profile_text = json.dumps(profile, indent=2, default=str)
        if len(profile_text) > 8000:
            profile_text = profile_text[:8000] + "\n... (truncated)"

        prompt = f"""Analyze this table profile and provide semantic descriptions.

{profile_text}

For each column, infer:
1. What the column likely represents in a business context
2. Its semantic type (e.g., identifier, metric, dimension, timestamp, category)
3. Any notable patterns in the sample values

Respond with a JSON object:
{{
  "table_description": "what this table likely contains",
  "columns": {{
    "column_name": {{
      "description": "what this column represents",
      "semantic_type": "metric|dimension|identifier|timestamp|category|text",
      "notes": "any observations"
    }}
  }}
}}"""

        try:
            return await self.llm.complete_json(
                [{"role": "user", "content": prompt}]
            )
        except Exception as e:
            logger.error(f"LLM interpretation failed: {e}")
            return {"table_description": profile.get("table_name", ""), "columns": {}}


data_profiler = DataProfiler()
