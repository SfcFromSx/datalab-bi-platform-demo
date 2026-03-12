from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.chatbi_agent import ChatBIAgent
from app.agents.context_builder import build_notebook_query_context
from app.models.datasource import DataSource, DataSourceType


@pytest.mark.asyncio
async def test_chatbi_agent_handles_sql_result(monkeypatch) -> None:
    async def fake_generate_sql_stream(query, context):
        yield "SELECT * FROM sales"

    def fake_execute_isolated(query, tables=None, datasource_ids=None, datasources=None):
        return {"status": "success", "columns": ["id", "amount"], "rows": [[1, 100]], "row_count": 1}

    from app.execution import sql_executor
    agent = ChatBIAgent()
    monkeypatch.setattr(agent, "_generate_sql_stream", fake_generate_sql_stream)
    monkeypatch.setattr(sql_executor, "execute_isolated", fake_execute_isolated)

    result = await agent.execute("how many sales", {"notebook_id": "nb-1"})

    assert result.action == "chat_bi_response"


@pytest.mark.asyncio
async def test_chatbi_stream_query_yields_steps(monkeypatch) -> None:
    async def fake_generate_sql_stream(query, context):
        yield "SELECT 1"

    def fake_execute_isolated(query, tables=None, datasource_ids=None, datasources=None):
        return {"status": "success", "columns": ["v"], "rows": [[1]], "row_count": 1}

    from app.execution import sql_executor
    agent = ChatBIAgent()
    monkeypatch.setattr(agent, "_generate_sql_stream", fake_generate_sql_stream)
    monkeypatch.setattr(sql_executor, "execute_isolated", fake_execute_isolated)

    steps = []
    async for step in agent.stream_query("count rows"):
        steps.append(step)

    types = [s["type"] for s in steps]
    assert "thinking" in types
    assert "sql" in types
    assert "executing" in types
    assert "data" in types
    assert "answer" in types


@pytest.mark.asyncio
async def test_chatbi_agent_includes_notebook_context_in_prompt(monkeypatch) -> None:
    captured_messages: list[dict[str, str]] = []

    async def fake_generate_sql_stream(query, context):
        captured_messages.append({"role": "user", "content": query})
        yield "SELECT * FROM context"

    agent = ChatBIAgent()
    monkeypatch.setattr(agent, "_generate_sql_stream", fake_generate_sql_stream)

    await agent.execute(
        "query this",
        {
            "notebook_context": "Previous results: [1, 2, 3]",
        },
    )

    assert len(captured_messages) >= 1
    user_prompt = captured_messages[-1]["content"]
    assert "Notebook context:\nPrevious results: [1, 2, 3]" in user_prompt


def test_build_notebook_query_context_includes_values_and_datasource() -> None:
    datasource = DataSource(
        id="ds-1",
        name="sales_csv",
        ds_type=DataSourceType.CSV,
        connection_string="/tmp/sales.csv",
        metadata_={"row_count": 2},
    )
    cells = [
        SimpleNamespace(
            id="cell-1",
            notebook_id="nb-1",
            cell_type="python",
            source="threshold = 10\nmetrics = {'max': 12}",
            output={
                "status": "success",
                "stdout": "",
                "stderr": "",
                "data": None,
                "exports": {"threshold": 10, "metrics": {"max": 12}},
                "error": None,
            },
            position=0,
            metadata_=None,
        ),
        SimpleNamespace(
            id="cell-2",
            notebook_id="nb-1",
            cell_type="markdown",
            source="Threshold {{ threshold }}",
            output=None,
            position=1,
            metadata_=None,
        ),
    ]

    context = build_notebook_query_context(
        cells,
        "Explain threshold",
        focus_cell_id="cell-2",
        datasource=datasource,
    )

    assert '"threshold": 10' in context["value_context"]
    assert context["available_bindings"] == ["metrics", "threshold"]
    assert "Data source: sales_csv (csv)" in context["datasource_context"]
    assert context["cell_context"][0]["cell_id"] == "cell-1"


@pytest.mark.asyncio
async def test_chatbi_agent_uses_isolated_execution_with_context(monkeypatch) -> None:
    from app.execution.sql_executor import sql_executor

    async def fake_generate_sql_stream(query, context):
        yield "SELECT * FROM test"

    captured_params = {}

    def fake_execute_isolated(query, tables=None, datasource_ids=None, datasources=None):
        captured_params["tables"] = tables
        captured_params["datasources"] = datasources
        return {"status": "success", "columns": ["a"], "rows": [[1]], "row_count": 1}

    monkeypatch.setattr(sql_executor, "execute_isolated", fake_execute_isolated)

    agent = ChatBIAgent()
    monkeypatch.setattr(agent, "_generate_sql_stream", fake_generate_sql_stream)

    ds = DataSource(id="ds-1", name="test_ds", ds_type=DataSourceType.CSV, connection_string="")
    raw_tables = {"prev_cell": {"columns": ["x"], "rows": [[1]]}}

    result = await agent.execute("test query", {
        "datasource": ds,
        "datasource_id": "ds-1",
        "datasources": [ds],
        "raw_tables": raw_tables
    })

    assert captured_params["tables"] == raw_tables
    assert len(captured_params["datasources"]) == 1
    assert captured_params["datasources"][0].id == "ds-1"
