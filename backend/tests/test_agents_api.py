from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.agents.chat_agent import ChatAgent
from app.agents.context_builder import build_notebook_query_context
from app.agents.proxy import ProxyAgent
from app.api import agents as agents_api
from app.communication.info_unit import InformationUnit
from app.models.datasource import DataSource, DataSourceType
from app.schemas.agent import AgentQueryRequest


class FakeSession:
    def __init__(self, notebooks: dict[str, object]):
        self._notebooks = notebooks

    async def get(self, _model, notebook_id: str):
        return self._notebooks.get(notebook_id)


@pytest.mark.asyncio
async def test_proxy_agent_wraps_chat_messages(monkeypatch) -> None:
    async def fake_chat_execute(query: str, context):
        return InformationUnit(content=f"Echo: {query}")

    monkeypatch.setattr("app.agents.proxy.chat_agent.execute", fake_chat_execute)

    result = await ProxyAgent().execute("hello", {"notebook_id": "nb-1"})

    assert result.action == "chat_only_response"
    assert result.content["message"] == "Echo: hello"
    assert result.content["task_id"]


@pytest.mark.asyncio
async def test_proxy_agent_returns_fallback_message_on_error(monkeypatch) -> None:
    async def failing_chat_execute(query: str, context):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr("app.agents.proxy.chat_agent.execute", failing_chat_execute)

    result = await ProxyAgent().execute("hello", None)

    assert result.action == "chat_only_response"
    assert "LLM unavailable" in result.content["message"]


@pytest.mark.asyncio
async def test_chat_agent_includes_notebook_context_in_prompt(monkeypatch) -> None:
    captured_messages: list[dict[str, str]] = []

    async def fake_call_llm(messages, temperature=0.0, max_tokens=4096):
        captured_messages.extend(messages)
        return "answer"

    agent = ChatAgent()
    monkeypatch.setattr(agent, "_call_llm", fake_call_llm)

    result = await agent.execute(
        "What does this notebook do?",
        {
            "notebook_context": "Cell a (sql)",
            "table_context": '{"sales_summary": {"columns": ["amount"], "rows": [[1]]}}',
            "value_context": '{"threshold": 10}',
            "datasource_context": "Data source: sales (csv)",
            "cell_context": [{"cell_id": "a", "cell_type": "sql"}],
            "available_bindings": ["sales_summary", "threshold"],
        },
    )

    assert result.content == "answer"
    assert len(captured_messages) == 2
    prompt = captured_messages[1]["content"]
    assert "Notebook context:" in prompt
    assert "Available tables:" in prompt
    assert "Available scalar values:" in prompt
    assert "Focused cell neighborhood:" in prompt
    assert "Notebook bindings: sales_summary, threshold" in prompt


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
        }

    async def fake_proxy_execute(query: str, context):
        captured_context.update(context)
        return InformationUnit(
            content={"task_id": "task-123", "message": f"Handled: {query}"}
        )

    monkeypatch.setattr(agents_api, "load_notebook_query_context", fake_load_context)
    monkeypatch.setattr(agents_api.proxy_agent, "execute", fake_proxy_execute)

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
async def test_agent_query_returns_error_response_when_proxy_fails(monkeypatch) -> None:
    async def fake_load_context(
        session,
        notebook_id,
        query,
        focus_cell_id=None,
        datasource_id=None,
    ):
        return {}

    async def failing_proxy_execute(query: str, context):
        raise RuntimeError("proxy failed")

    monkeypatch.setattr(agents_api, "load_notebook_query_context", fake_load_context)
    monkeypatch.setattr(agents_api.proxy_agent, "execute", failing_proxy_execute)

    response = await agents_api.agent_query(
        AgentQueryRequest(query="hello", notebook_id="nb-1"),
        session=FakeSession({"nb-1": SimpleNamespace(id="nb-1")}),
    )

    assert response.status == "error"
    assert response.message == "proxy failed"
    assert response.task_id
