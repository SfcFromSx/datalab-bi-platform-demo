from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.execution.cell_runtime import CellRuntime
from app.execution.python_executor import PythonExecutor
from app.execution.sql_executor import SQLExecutor
from app.models.datasource import DataSource, DataSourceType


@pytest.mark.asyncio
async def test_python_executor_supports_bootstrap_tables_and_captures_data() -> None:
    executor = PythonExecutor()
    result = await executor.execute(
        (
            "result_df = sales_summary.assign("
            "total=sales_summary['amount'] + bonus"
            ")\n"
            "print(int(result_df['total'].sum()))"
        ),
        bootstrap_code="bonus = 5",
        bootstrap_tables={
            "sales_summary": {
                "columns": ["amount"],
                "rows": [[1], [2]],
            }
        },
    )

    assert result["status"] == "success"
    assert result["stdout"] == "13\n"
    assert result["data"]["variable"] == "result_df"
    assert result["data"]["columns"] == ["amount", "total"]
    assert result["data"]["rows"] == [[1, 6], [2, 7]]
    assert result["exports"] == {}


@pytest.mark.asyncio
async def test_python_executor_exports_json_safe_scalar_values() -> None:
    executor = PythonExecutor()
    result = await executor.execute(
        (
            "threshold = base + 3\n"
            "metrics = {'threshold': threshold, 'labels': ['a', 'b']}\n"
            "notes = f'value={threshold}'\n"
        ),
        bootstrap_values={"base": 7},
    )

    assert result["status"] == "success"
    assert result["exports"] == {
        "threshold": 10,
        "metrics": {"threshold": 10, "labels": ["a", "b"]},
        "notes": "value=10",
    }


@pytest.mark.asyncio
async def test_python_executor_reports_errors() -> None:
    executor = PythonExecutor()
    result = await executor.execute("raise ValueError('boom')")

    assert result["status"] == "error"
    assert "ValueError: boom" in result["error"]


@pytest.mark.asyncio
async def test_python_executor_reports_timeouts() -> None:
    executor = PythonExecutor()
    executor.timeout = 0.01

    result = await executor.execute("import time\ntime.sleep(0.1)")

    assert result["status"] == "error"
    assert "timed out" in result["error"]


def test_sql_executor_executes_queries_and_serializes_temporal_values() -> None:
    executor = SQLExecutor()
    executor.register_dataframe("sales", pd.DataFrame({"amount": [1, 2]}))

    assert "sales" in executor.get_tables()
    schema = executor.get_schema("sales")
    assert schema[0]["column_name"] == "amount"
    assert schema[0]["column_type"]

    result = executor.execute(
        (
            "SELECT "
            "DATE '2024-01-02' AS day, "
            "TIME '10:20:30' AS at_time, "
            "TIMESTAMP '2024-01-02 10:20:30' AS at_ts"
        )
    )
    assert result["status"] == "success"
    assert result["rows"] == [["2024-01-02", "10:20:30", "2024-01-02T10:20:30"]]

    error_result = executor.execute("SELECT * FROM missing_table")
    assert error_result["status"] == "error"
    assert "missing_table" in error_result["error"]


def test_sql_executor_execute_isolated_supports_tables_and_datasources(tmp_path: Path) -> None:
    executor = SQLExecutor()
    executor.register_dataframe(
        "registered_sales",
        pd.DataFrame({"amount": [4, 5]}),
        datasource_id="registered-ds",
    )

    registered_result = executor.execute_isolated(
        "SELECT SUM(amount) AS total_amount FROM registered_sales",
        datasource_ids=["registered-ds"],
    )
    assert registered_result["rows"] == [[9]]

    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("amount,category\n2,A\n3,B\n", encoding="utf-8")
    csv_datasource = DataSource(
        id="csv-ds",
        name="sales_csv",
        ds_type=DataSourceType.CSV,
        connection_string=str(csv_path),
    )
    csv_result = executor.execute_isolated(
        "SELECT COUNT(*) AS row_count FROM sales_csv",
        datasources=[csv_datasource],
    )
    assert csv_result["rows"] == [[2]]

    tables_result = executor.execute_isolated(
        "SELECT AVG(amount) AS avg_amount FROM provided_table",
        tables={"provided_table": {"columns": ["amount"], "rows": [[2], [4], [6]]}},
    )
    assert tables_result["rows"] == [[4.0]]


@pytest.mark.asyncio
async def test_cell_runtime_executes_linked_notebook_flow(runtime_cells, tmp_path: Path) -> None:
    runtime = CellRuntime(root_dir=tmp_path)

    chart_run = await runtime.execute_target(runtime_cells, "cell-chart")
    assert chart_run.plan == ["cell-sql", "cell-python", "cell-chart"]
    assert chart_run.outputs_by_id["cell-chart"]["chart"] == {
        "data_source": "enriched",
        "columns": ["amount", "category", "double_amount"],
        "row_count": 2,
    }
    assert chart_run.outputs_by_id["cell-python"]["agent"]["input_messages"] == 1
    assert chart_run.outputs_by_id["cell-python"]["agent"]["published_messages"] == 1
    chart_inbox = chart_run.paths_by_id["cell-chart"].inbox_dir / "from-cell-python.json"
    assert chart_inbox.exists()

    markdown_run = await runtime.execute_target(runtime_cells, "cell-markdown")
    assert markdown_run.plan == ["cell-sql", "cell-python", "cell-markdown"]
    assert "Rows 2" in markdown_run.outputs_by_id["cell-markdown"]["html"]
    assert "amount, category, double_amount" in markdown_run.outputs_by_id["cell-markdown"]["html"]
    assert markdown_run.outputs_by_id["cell-markdown"]["bindings"] == [
        "enriched",
        "sales_summary",
    ]

    description = runtime.describe_cell(runtime_cells, "cell-chart")
    assert description["plan"] == ["cell-sql", "cell-python", "cell-chart"]
    assert description["dependencies"] == ["cell-python"]

    edit_task = runtime.write_edit_task(runtime_cells, "cell-python", "Add a filter")
    assert Path(edit_task["task_file"]).exists()
    assert Path(edit_task["context_file"]).exists()


@pytest.mark.asyncio
async def test_cell_runtime_transfers_scalar_values_without_replaying_ancestor_side_effects(
    tmp_path: Path,
) -> None:
    runtime = CellRuntime(root_dir=tmp_path)
    scalar_cells = [
        type("Cell", (), {
            "id": "cell-python-1",
            "notebook_id": "nb-values",
            "cell_type": "python",
            "source": "print('seed side effect')\nthreshold = 10\nmetrics = {'max': 12}",
            "output": None,
            "position": 0,
            "metadata_": None,
        })(),
        type("Cell", (), {
            "id": "cell-markdown",
            "notebook_id": "nb-values",
            "cell_type": "markdown",
            "source": "Threshold {{ threshold }} | Max {{ metrics.max }}",
            "output": None,
            "position": 1,
            "metadata_": None,
        })(),
        type("Cell", (), {
            "id": "cell-python-2",
            "notebook_id": "nb-values",
            "cell_type": "python",
            "source": "result = threshold + 1\nprint(result)",
            "output": None,
            "position": 2,
            "metadata_": None,
        })(),
    ]

    markdown_run = await runtime.execute_target(scalar_cells, "cell-markdown")
    assert markdown_run.outputs_by_id["cell-markdown"]["html"] == "Threshold 10 | Max 12"
    assert markdown_run.outputs_by_id["cell-markdown"]["bindings"] == ["metrics", "threshold"]

    python_run = await runtime.execute_target(scalar_cells, "cell-python-2")
    assert python_run.outputs_by_id["cell-python-2"]["stdout"] == "11\n"
    assert python_run.outputs_by_id["cell-python-2"]["exports"] == {"result": 11}
    assert python_run.outputs_by_id["cell-python-2"]["agent"]["bootstrap_file"] is None


@pytest.mark.asyncio
async def test_cell_runtime_replays_required_python_helpers_when_values_are_not_exportable(
    tmp_path: Path,
) -> None:
    runtime = CellRuntime(root_dir=tmp_path)
    helper_cells = [
        type("Cell", (), {
            "id": "cell-helper",
            "notebook_id": "nb-helper",
            "cell_type": "python",
            "source": "def helper(value):\n    return value + 2",
            "output": None,
            "position": 0,
            "metadata_": None,
        })(),
        type("Cell", (), {
            "id": "cell-target",
            "notebook_id": "nb-helper",
            "cell_type": "python",
            "source": "result = helper(3)\nprint(result)",
            "output": None,
            "position": 1,
            "metadata_": None,
        })(),
    ]

    run = await runtime.execute_target(helper_cells, "cell-target")

    assert run.outputs_by_id["cell-target"]["stdout"] == "5\n"
    bootstrap_file = Path(run.paths_by_id["cell-target"].bootstrap_file)
    assert bootstrap_file.exists()
    assert "def helper(value)" in bootstrap_file.read_text(encoding="utf-8")


def test_cell_runtime_helper_errors_and_placeholders(tmp_path: Path) -> None:
    runtime = CellRuntime(root_dir=tmp_path)

    invalid_json = runtime._execute_chart_cell("not json", {})
    assert invalid_json["status"] == "error"

    missing_table = runtime._execute_chart_cell('{"data_source":"missing"}', {})
    assert missing_table["status"] == "error"
    assert "missing" in missing_table["error"]

    resolved = runtime._render_markdown_placeholders(
        "Rows {{ table.row_count }} | Missing {{ other.row_count }}",
        {"table": {"columns": ["amount"], "rows": [[1], [2], [3]]}},
    )
    assert resolved == "Rows 3 | Missing {{ other.row_count }}"

    assert runtime._resolve_chart_data_source(
        {"dataset": {"sourceVariable": "table"}}
    ) == "table"
