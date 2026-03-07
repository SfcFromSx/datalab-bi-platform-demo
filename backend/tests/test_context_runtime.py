from __future__ import annotations

import json

from app.context.dag import CellDependencyDAG
from app.context.tracker import variable_tracker
from app.notebook_runtime import (
    build_cell_context,
    build_python_bootstrap,
    build_query_context,
    build_runtime_bundle,
    build_sql_bootstrap_tables,
    build_value_catalog,
    extract_output_table,
    extract_output_values,
    extract_variable_names,
    summarize_output,
)


def test_variable_tracker_handles_supported_cell_types() -> None:
    python_result = variable_tracker.analyze_cell(
        "py-1",
        "python",
        (
            "import math as math_alias\n"
            "from collections import Counter\n"
            "x = 1\n"
            "y, z = external_pair\n"
            "x += delta\n"
            "class Foo:\n"
            "    pass\n"
            "def bar():\n"
            "    return helper\n"
            "print(math_alias.pi, external_value, Counter([1, 1]))\n"
        ),
    )
    assert python_result.defined >= {"math_alias", "Counter", "x", "y", "z", "Foo", "bar"}
    assert python_result.referenced >= {"external_pair", "delta", "helper", "external_value"}
    assert "print" not in python_result.referenced
    assert "int" not in python_result.referenced

    sql_result = variable_tracker.analyze_cell(
        "sql-1",
        "sql",
        (
            "-- output: sales_summary\n"
            "SELECT * FROM sales\n"
            "JOIN products ON sales.product_id = products.id"
        ),
    )
    assert sql_result.defined == {"sales_summary"}
    assert sql_result.referenced == {"sales", "products"}

    chart_result = variable_tracker.analyze_cell(
        "chart-1",
        "chart",
        '{"data_source":"sales_summary","dataset":{"sourceVariable":"enriched"}}',
    )
    assert chart_result.referenced == {"sales_summary", "enriched"}

    markdown_result = variable_tracker.analyze_cell(
        "md-1",
        "markdown",
        "Rows {{ sales_summary.row_count }} and {{ enriched.columns }}",
    )
    assert markdown_result.referenced == {"sales_summary", "enriched"}

    unknown_result = variable_tracker.analyze_cell("other-1", "other", "noop")
    assert unknown_result.defined == set()
    assert unknown_result.referenced == set()


def test_dag_tracks_redefinitions_and_execution_plan() -> None:
    dag = CellDependencyDAG()
    dag.build(
        [
            {"id": "cell1", "cell_type": "python", "source": "x = 1", "position": 0},
            {"id": "cell2", "cell_type": "python", "source": "y = x + 1", "position": 1},
            {"id": "cell3", "cell_type": "python", "source": "z = y + x", "position": 2},
            {"id": "cell4", "cell_type": "python", "source": "x = 5", "position": 3},
            {"id": "cell5", "cell_type": "python", "source": "w = x + 1", "position": 4},
        ]
    )

    assert dag.get_direct_dependencies("cell3") == ["cell1", "cell2"]
    assert dag.get_direct_dependencies("cell5") == ["cell4"]
    assert dag.get_descendants("cell1") == {"cell2", "cell3"}
    assert dag.get_execution_plan("cell3") == ["cell1", "cell2", "cell3"]
    assert dag.get_execution_plan("cell5") == ["cell4", "cell5"]

    dag.update_cell("cell4", "python", "x = y + 10")
    assert dag.get_direct_dependencies("cell4") == ["cell2"]

    dag.remove_cell("cell2")
    assert dag.get_direct_dependencies("cell3") == ["cell1"]
    assert dag.get_direct_dependencies("cell4") == []
    assert dag.get_direct_dependencies("cell5") == ["cell4"]


def test_runtime_bundle_and_context_retrieval_are_deterministic(runtime_cells) -> None:
    bundle = build_runtime_bundle(runtime_cells)

    assert [cell["id"] for cell in bundle.ordered_cells] == [
        "cell-sql",
        "cell-python",
        "cell-chart",
        "cell-markdown",
    ]
    assert bundle.cells_by_id["cell-python"]["variables_defined"] == ["enriched"]
    assert bundle.cells_by_id["cell-python"]["variables_referenced"] == ["sales_summary"]

    cell_context = build_cell_context(bundle, "cell-markdown")
    assert [cell["cell_id"] for cell in cell_context] == [
        "cell-sql",
        "cell-python",
        "cell-markdown",
    ]

    notebook_context = bundle.retriever.retrieve_notebook_context(
        "sales_summary",
        task_type="general",
        cells_data=bundle.cells_by_id,
    )
    assert [cell["cell_id"] for cell in notebook_context] == [
        "cell-sql",
        "cell-python",
        "cell-chart",
        "cell-markdown",
    ]

    query_context = build_query_context(
        bundle,
        query="double amount chart",
        focus_cell_id="cell-chart",
        task_type="nl2vis",
        limit=3,
    )
    assert [cell["cell_id"] for cell in query_context["cells"]] == [
        "cell-sql",
        "cell-python",
        "cell-chart",
    ]
    assert "Cell cell-python (python)" in query_context["notebook_context"]

    table_context = json.loads(query_context["table_context"])
    assert set(table_context) == {"sales_summary", "enriched"}
    value_context = json.loads(query_context["value_context"])
    assert value_context == {}


def test_runtime_bootstrap_and_output_helpers(runtime_cells) -> None:
    bundle = build_runtime_bundle(runtime_cells)

    bootstrap_code, bootstrap_tables = build_python_bootstrap(bundle, "cell-chart")
    assert "enriched = sales_summary.assign" in bootstrap_code
    assert set(bootstrap_tables) == {"sales_summary", "enriched"}

    sql_bootstrap = build_sql_bootstrap_tables(bundle, "cell-chart")
    assert set(sql_bootstrap) == {"sales_summary", "enriched"}

    sql_cell = bundle.cells_by_id["cell-sql"]
    python_cell = bundle.cells_by_id["cell-python"]
    markdown_cell = bundle.cells_by_id["cell-markdown"]

    assert extract_variable_names(sql_cell) == ["sales_summary"]
    assert extract_variable_names(python_cell) == ["enriched"]
    assert extract_variable_names(markdown_cell) == []
    assert extract_output_values(sql_cell) == {}
    assert extract_output_values(python_cell) == {}
    assert build_value_catalog([sql_cell, python_cell]) == {}

    assert extract_output_table(sql_cell) == {
        "columns": ["amount", "category"],
        "rows": [[2, "A"], [3, "B"]],
    }
    assert summarize_output(python_cell["output"]) == (
        "DataFrame enriched with columns ['amount', 'category', 'double_amount'] and 2 rows | 10\n"
    )
    assert summarize_output({"status": "error", "error": "boom"}) == "boom"
    assert summarize_output({"status": "success", "stdout": "preview"}) == "preview"


def test_query_context_falls_back_to_recent_cells(runtime_cells) -> None:
    bundle = build_runtime_bundle(runtime_cells)

    fallback_context = bundle.retriever.retrieve_query_context(
        "nothing in this query matches",
        task_type="general",
        cells_data=bundle.cells_by_id,
        limit=2,
    )
    assert [cell["cell_id"] for cell in fallback_context] == [
        "cell-chart",
        "cell-markdown",
    ]
