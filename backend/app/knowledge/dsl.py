"""DSL Translator - Convert natural language queries to structured DSL specifications.

The DSL includes:
- MeasureList: numerical columns with aggregation
- DimensionList: categorical columns for grouping
- ConditionList: filters
- OrderBy, Limit, ChartType
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.llm.client import LLMClient, llm_client

logger = logging.getLogger(__name__)

DSL_SCHEMA = {
    "type": "object",
    "properties": {
        "MeasureList": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "aggregation": {"type": "string", "enum": ["SUM", "COUNT", "AVG", "MIN", "MAX", "NONE"]},
                    "alias": {"type": "string"},
                },
                "required": ["column"],
            },
        },
        "DimensionList": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                },
                "required": ["column"],
            },
        },
        "ConditionList": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "operator": {"type": "string"},
                    "value": {},
                },
                "required": ["column", "operator", "value"],
            },
        },
        "OrderBy": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "direction": {"type": "string", "enum": ["ASC", "DESC"]},
                },
            },
        },
        "Limit": {"type": ["integer", "null"]},
        "ChartType": {
            "type": ["string", "null"],
            "enum": ["bar", "line", "pie", "scatter", "heatmap", "area", "table", None],
        },
    },
}


class DSLTranslator:
    """Translate natural language queries to structured DSL specifications."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or llm_client

    async def translate(
        self,
        query: str,
        schema: str,
        knowledge: str = "",
    ) -> dict[str, Any]:
        from app.agents.base import _jinja_env

        template = _jinja_env.get_template("dsl_translation.j2")
        prompt = template.render(
            query=query,
            schema=schema,
            knowledge=knowledge or None,
        )

        messages = [
            {"role": "system", "content": "You are a DSL translation expert."},
            {"role": "user", "content": prompt},
        ]

        dsl = await self.llm.complete_json(messages)
        validated = self._validate_dsl(dsl)
        return validated

    def _validate_dsl(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize the DSL specification."""
        validated = {
            "MeasureList": [],
            "DimensionList": [],
            "ConditionList": [],
            "OrderBy": [],
            "Limit": None,
            "ChartType": None,
        }

        for measure in dsl.get("MeasureList", []):
            if isinstance(measure, dict) and "column" in measure:
                validated["MeasureList"].append({
                    "column": measure["column"],
                    "aggregation": measure.get("aggregation", "NONE"),
                    "alias": measure.get("alias", measure["column"]),
                })

        for dim in dsl.get("DimensionList", []):
            if isinstance(dim, dict) and "column" in dim:
                validated["DimensionList"].append({"column": dim["column"]})

        for cond in dsl.get("ConditionList", []):
            if isinstance(cond, dict) and all(k in cond for k in ("column", "operator", "value")):
                validated["ConditionList"].append(cond)

        for order in dsl.get("OrderBy", []):
            if isinstance(order, dict) and "column" in order:
                validated["OrderBy"].append({
                    "column": order["column"],
                    "direction": order.get("direction", "ASC"),
                })

        limit = dsl.get("Limit")
        if isinstance(limit, int) and limit > 0:
            validated["Limit"] = limit

        chart_type = dsl.get("ChartType")
        valid_types = {"bar", "line", "pie", "scatter", "heatmap", "area", "table"}
        if chart_type in valid_types:
            validated["ChartType"] = chart_type

        return validated

    def dsl_to_sql(self, dsl: dict[str, Any], table_name: str) -> str:
        """Convert a DSL specification to a SQL query."""
        select_parts = []

        for dim in dsl.get("DimensionList", []):
            select_parts.append(f'"{dim["column"]}"')

        for measure in dsl.get("MeasureList", []):
            col = f'"{measure["column"]}"'
            agg = measure.get("aggregation", "NONE")
            alias = measure.get("alias", measure["column"])
            if agg and agg != "NONE":
                select_parts.append(f'{agg}({col}) AS "{alias}"')
            else:
                select_parts.append(f'{col} AS "{alias}"')

        if not select_parts:
            select_parts = ["*"]

        sql = f'SELECT {", ".join(select_parts)} FROM "{table_name}"'

        conditions = dsl.get("ConditionList", [])
        if conditions:
            where_parts = []
            for c in conditions:
                val = f"'{c['value']}'" if isinstance(c["value"], str) else str(c["value"])
                where_parts.append(f'"{c["column"]}" {c["operator"]} {val}')
            sql += f' WHERE {" AND ".join(where_parts)}'

        dims = dsl.get("DimensionList", [])
        has_agg = any(
            m.get("aggregation", "NONE") != "NONE"
            for m in dsl.get("MeasureList", [])
        )
        if dims and has_agg:
            group_cols = [f'"{d["column"]}"' for d in dims]
            sql += f' GROUP BY {", ".join(group_cols)}'

        for order in dsl.get("OrderBy", []):
            sql += f' ORDER BY "{order["column"]}" {order.get("direction", "ASC")}'

        limit = dsl.get("Limit")
        if limit:
            sql += f" LIMIT {limit}"

        return sql


dsl_translator = DSLTranslator()
