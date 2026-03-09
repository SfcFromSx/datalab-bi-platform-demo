from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.agents.chatbi_agent import ChatBIAgent
from app.agents.context_builder import build_notebook_query_context
from app.api import agents as agents_api
from app.communication.info_unit import InformationUnit
from app.models.datasource import DataSource, DataSourceType
from app.schemas.agent import AgentQueryRequest


class FakeSession:
    def __init__(self, notebooks: dict[str, object], datasources: list[DataSource] = None):
        self._notebooks = notebooks
        self._datasources = datasources or []

    async def get(self, _model, notebook_id: str):
        return self._notebooks.get(notebook_id)
        
    async def execute(self, statement):
        class Result:
            def __init__(self, items): self.items = items
            def scalars(self): return self
            def all(self): return self.items
        return Result(self._datasources)


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
    assert "SELECT * FROM sales" in result.content["message"]
    # Table formatting check
    assert "| id | amount |" in result.content["message"]
    assert "| 1 | 100 |" in result.content["message"]


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

    # User prompt
    assert len(captured_messages) >= 1
    user_prompt = captured_messages[-1]["content"]
    assert "Context:\nPrevious results: [1, 2, 3]" in user_prompt


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
async def test_agent_query_returns_completed_response(monkeypatch) -> None:
    captured_context: dict[str, object] = {}

    async def fake_load_context(
        session,
        notebook_id,
        query,
        focus_cell_id=None,
        datasource_id=None,
    ):
        return {
            "notebook_context": "Cell a (sql)",
            "table_context": "{}",
            "value_context": '{"threshold": 10}',
            "cell_context": [],
            "datasource_context": "",
            "available_bindings": ["threshold"],
            "raw_tables": {},
            "datasources": []
        }

    async def fake_chatbi_execute(query: str, context):
        captured_context.update(context)
        return InformationUnit(
            content={"task_id": "task-123", "message": f"Handled: {query}", "results": []}
        )

    monkeypatch.setattr(agents_api, "load_notebook_query_context", fake_load_context)
    monkeypatch.setattr(agents_api.chatbi_agent, "execute", fake_chatbi_execute)

    response = await agents_api.agent_query(
        AgentQueryRequest(query="hello", notebook_id="nb-1"),
        session=FakeSession({"nb-1": SimpleNamespace(id="nb-1")}),
    )

    assert response.status == "completed"
    assert response.task_id == "task-123"
    assert response.message == "Handled: hello"
    assert response.cells_created == []
    assert captured_context["available_bindings"] == ["threshold"]


@pytest.mark.asyncio
async def test_agent_query_raises_not_found_for_missing_notebook() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await agents_api.agent_query(
            AgentQueryRequest(query="hello", notebook_id="missing"),
            session=FakeSession({}),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Notebook not found"


@pytest.mark.asyncio
async def test_agent_query_returns_error_response_when_agent_fails(monkeypatch) -> None:
    async def fake_load_context(
        session,
        notebook_id,
        query,
        focus_cell_id=None,
        datasource_id=None,
    ):
        return {}

    async def failing_agent_execute(query: str, context):
        raise RuntimeError("agent failed")

    monkeypatch.setattr(agents_api, "load_notebook_query_context", fake_load_context)
    monkeypatch.setattr(agents_api.chatbi_agent, "execute", failing_agent_execute)

    response = await agents_api.agent_query(
        AgentQueryRequest(query="hello", notebook_id="nb-1"),
        session=FakeSession({"nb-1": SimpleNamespace(id="nb-1")}),
    )

    assert response.status == "error"
    assert response.message == "agent failed"
    assert response.task_id


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
