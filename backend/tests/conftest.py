from __future__ import annotations

from types import SimpleNamespace

import pytest


def make_cell(
    *,
    cell_id: str,
    cell_type: str,
    source: str,
    position: int,
    notebook_id: str = "nb-demo",
    output: dict | None = None,
    metadata: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=cell_id,
        notebook_id=notebook_id,
        cell_type=cell_type,
        source=source,
        output=output,
        position=position,
        metadata_=metadata,
    )


@pytest.fixture
def runtime_cells() -> list[SimpleNamespace]:
    return [
        make_cell(
            cell_id="cell-sql",
            cell_type="sql",
            position=0,
            source=(
                "-- output: sales_summary\n"
                "SELECT 2 AS amount, 'A' AS category\n"
                "UNION ALL\n"
                "SELECT 3 AS amount, 'B' AS category"
            ),
            output={
                "status": "success",
                "columns": ["amount", "category"],
                "rows": [[2, "A"], [3, "B"]],
                "row_count": 2,
                "error": None,
            },
        ),
        make_cell(
            cell_id="cell-python",
            cell_type="python",
            position=1,
            source=(
                "enriched = sales_summary.assign("
                "double_amount=sales_summary['amount'] * 2"
                ")\n"
                "print(int(enriched['double_amount'].sum()))"
            ),
            output={
                "status": "success",
                "stdout": "10\n",
                "stderr": "",
                "data": {
                    "columns": ["amount", "category", "double_amount"],
                    "rows": [[2, "A", 4], [3, "B", 6]],
                    "shape": [2, 3],
                    "variable": "enriched",
                },
                "error": None,
            },
        ),
        make_cell(
            cell_id="cell-chart",
            cell_type="chart",
            position=2,
            source='{"data_source":"enriched","mark":"bar"}',
            output={
                "status": "success",
                "error": None,
                "chart": {
                    "data_source": "enriched",
                    "columns": ["amount", "category", "double_amount"],
                    "row_count": 2,
                },
            },
        ),
        make_cell(
            cell_id="cell-markdown",
            cell_type="markdown",
            position=3,
            source=(
                "Rows {{ enriched.row_count }} | "
                "Columns {{ enriched.columns }} | "
                "Preview {{ enriched.preview }}"
            ),
            output={
                "status": "success",
                "html": "Rows 2",
                "error": None,
            },
        ),
    ]
