"""SQL execution engine using DuckDB for in-process OLAP queries."""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence

import duckdb
import pandas as pd

from app.models.datasource import DataSource, DataSourceType

logger = logging.getLogger(__name__)


class SQLExecutor:
    """Execute SQL queries using DuckDB (in-process, zero-config OLAP engine)."""

    def __init__(self):
        self._connections: dict[str, duckdb.DuckDBPyConnection] = {}
        self._default_conn = duckdb.connect(":memory:")

    def _get_connection(self, datasource_id: Optional[str] = None) -> duckdb.DuckDBPyConnection:
        if datasource_id:
            if datasource_id not in self._connections:
                self._connections[datasource_id] = duckdb.connect(":memory:")
            return self._connections[datasource_id]
        return self._default_conn

    def register_csv(self, table_name: str, file_path: str, datasource_id: Optional[str] = None):
        conn = self._get_connection(datasource_id)
        conn.execute(
            f'CREATE OR REPLACE TABLE "{table_name}" AS '
            f"SELECT * FROM read_csv_auto('{file_path}')"
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
            return self._run_query(conn, query)
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return {
                "status": "error",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e),
            }

    def execute_isolated(
        self,
        query: str,
        tables: dict[str, dict[str, Any]] | None = None,
        datasource_ids: Sequence[str] | None = None,
        datasources: Sequence[DataSource] | None = None,
    ) -> dict[str, Any]:
        conn = duckdb.connect(":memory:")
        try:
            for datasource in datasources or []:
                self._import_datasource(conn, datasource)
            for datasource_id in datasource_ids or []:
                self._import_datasource_tables(conn, datasource_id)
            for table_name, table_data in (tables or {}).items():
                columns = table_data.get("columns") or []
                if not columns:
                    continue
                rows = table_data.get("rows") or []
                conn.register(table_name, pd.DataFrame(rows, columns=columns))
            return self._run_query(conn, query)
        except Exception as e:
            logger.error(f"Isolated SQL execution error: {e}")
            return {
                "status": "error",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e),
            }
        finally:
            conn.close()

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

    def _import_datasource_tables(
        self,
        target_conn: duckdb.DuckDBPyConnection,
        datasource_id: str,
    ) -> None:
        source_conn = self._get_connection(datasource_id)
        for table_name in self.get_tables(datasource_id):
            frame = source_conn.execute(f'SELECT * FROM "{table_name}"').fetchdf()
            target_conn.register(table_name, frame)

    def _import_datasource(
        self,
        target_conn: duckdb.DuckDBPyConnection,
        datasource: DataSource,
    ) -> None:
        imported_tables = self.get_tables(datasource.id)
        if imported_tables:
            self._import_datasource_tables(target_conn, datasource.id)
            return

        if datasource.ds_type == DataSourceType.CSV and datasource.connection_string:
            escaped_path = datasource.connection_string.replace("'", "''")
            target_conn.execute(
                f'CREATE OR REPLACE TABLE "{datasource.name}" AS '
                f"SELECT * FROM read_csv_auto('{escaped_path}')"
            )

    @staticmethod
    def _run_query(
        conn: duckdb.DuckDBPyConnection,
        query: str,
    ) -> dict[str, Any]:
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


sql_executor = SQLExecutor()
