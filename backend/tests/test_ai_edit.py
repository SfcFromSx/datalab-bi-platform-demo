from __future__ import annotations

from app.api.cells import _normalize_ai_edit_output
from app.models.cell import CellType


def test_normalize_ai_edit_output_preserves_current_source_on_invalid_python() -> None:
    current_source = "value = 1\nprint(value)"
    content = "```python\nvalue = (\n```"

    normalized = _normalize_ai_edit_output(CellType.PYTHON, current_source, content)

    assert normalized == current_source


def test_normalize_ai_edit_output_preserves_chart_contract_and_rejects_invalid_json() -> None:
    current_source = '{"data_source":"sales_summary","mark":"bar"}'

    invalid_json = _normalize_ai_edit_output(
        CellType.CHART,
        current_source,
        "```json\nnot valid json\n```",
    )
    assert invalid_json == current_source

    non_object = _normalize_ai_edit_output(
        CellType.CHART,
        current_source,
        '["not", "an", "object"]',
    )
    assert non_object == current_source

    valid_object = _normalize_ai_edit_output(
        CellType.CHART,
        current_source,
        '{"mark":"line"}',
    )
    assert '"data_source": "sales_summary"' in valid_object
