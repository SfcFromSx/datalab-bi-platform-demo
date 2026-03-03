"""SQL execution engine using DuckDB for in-process OLAP queries."""

from __future__ import annotations

import logging
from typing import Any, Optional

import duckdb

logger = logging.getLogger(__name__)


class SQLExecutor:
    """Execute SQL queries using DuckDB (in-process, zero-config OLAP engine)."""

    def __init__(self):
        self._connections: dict[str, duckdb.DuckDBPyConnection] = {}
        self._default_conn = duckdb.connect(":memory:")

    def _get_connection(self, datasource_id: Optional[str] = None) -> duckdb.DuckDBPyConnection:
        if datasource_id and datasource_id in self._connections:
            return self._connections[datasource_id]
        return self._default_conn

    def register_csv(self, table_name: str, file_path: str, datasource_id: Optional[str] = None):
        conn = self._get_connection(datasource_id)
        conn.execute(
            f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM read_csv_auto('{file_path}')"
        )
        logger.info(f"Registered CSV '{file_path}' as table '{table_name}'")

    def register_dataframe(self, table_name: str, df: Any, datasource_id: Optional[str] = None):
        conn = self._get_connection(datasource_id)
        conn.register(table_name, df)
        logger.info(f"Registered DataFrame as table '{table_name}'")

    def execute(
        self, query: str, datasource_id: Optional[str] = None
    ) -> dict[str, Any]:
        conn = self._get_connection(datasource_id)
        try:
            result = conn.execute(query)
            if result.description:
                columns = [desc[0] for desc in result.description]
                rows = result.fetchall()
                return {
                    "status": "success",
                    "columns": columns,
                    "rows": [list(row) for row in rows[:500]],
                    "row_count": len(rows),
                    "error": None,
                }
            return {
                "status": "success",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": None,
            }
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return {
                "status": "error",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e),
            }

    def get_tables(self, datasource_id: Optional[str] = None) -> list[str]:
        conn = self._get_connection(datasource_id)
        result = conn.execute("SHOW TABLES")
        return [row[0] for row in result.fetchall()]

    def get_schema(
        self, table_name: str, datasource_id: Optional[str] = None
    ) -> list[dict[str, str]]:
        conn = self._get_connection(datasource_id)
        try:
            result = conn.execute(f"DESCRIBE \"{table_name}\"")
            return [
                {"column_name": row[0], "column_type": row[1]}
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Schema fetch error: {e}")
            return []


sql_executor = SQLExecutor()
