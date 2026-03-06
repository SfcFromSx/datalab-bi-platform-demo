from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.cells import _normalize_ai_edit_output
from app.agents.proxy import AGENT_REGISTRY, ProxyAgent
from app.cell_agents import cell_agent_runtime
from app.communication.info_unit import InformationUnit
from app.context.dag import CellDependencyDAG
from app.database import Base, get_session
from app.llm.client import llm_client
from app.main import app
from app.models import Cell, CellType, Notebook, User, Workspace, WorkspaceMembership, WorkspaceRole
from app.notebook_runtime import build_runtime_bundle, build_table_catalog


@pytest.fixture
async def enterprise_client(tmp_path) -> AsyncIterator[tuple[AsyncClient, dict[str, str]]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'enterprise-test.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    original_runtime_root = cell_agent_runtime.root_dir
    cell_agent_runtime.root_dir = tmp_path / "cell_agents"
    cell_agent_runtime.root_dir.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session

    async with session_factory() as session:
        workspace_alpha = Workspace(
            name="Workspace Alpha",
            slug="workspace-alpha",
            description="Primary workspace",
        )
        workspace_beta = Workspace(
            name="Workspace Beta",
            slug="workspace-beta",
            description="Secondary workspace",
        )
        admin = User(email="admin@example.com", display_name="Admin")
        analyst = User(email="analyst@example.com", display_name="Analyst")
        session.add_all([workspace_alpha, workspace_beta, admin, analyst])
        await session.flush()

        session.add_all(
            [
                WorkspaceMembership(
                    workspace_id=workspace_alpha.id,
                    user_id=admin.id,
                    role=WorkspaceRole.OWNER,
                ),
                WorkspaceMembership(
                    workspace_id=workspace_beta.id,
                    user_id=admin.id,
                    role=WorkspaceRole.OWNER,
                ),
                WorkspaceMembership(
                    workspace_id=workspace_alpha.id,
                    user_id=analyst.id,
                    role=WorkspaceRole.ANALYST,
                ),
            ]
        )
        await session.flush()

        beta_notebook = Notebook(
            workspace_id=workspace_beta.id,
            title="Beta Notebook",
            description="Scoped notebook",
        )
        session.add(beta_notebook)
        await session.flush()

        beta_cell = Cell(
            workspace_id=workspace_beta.id,
            notebook_id=beta_notebook.id,
            cell_type=CellType.SQL,
            source="select 1",
            position=0,
        )
        session.add(beta_cell)
        await session.commit()

    headers = {
        "admin_alpha": "workspace-alpha|admin@example.com",
        "admin_beta": "workspace-beta|admin@example.com",
        "analyst_alpha": "workspace-alpha|analyst@example.com",
    }

    def build_headers(key: str) -> dict[str, str]:
        workspace, user = headers[key].split("|", maxsplit=1)
        return {
            "X-DataLab-Workspace": workspace,
            "X-DataLab-User-Email": user,
        }

    ids = {
        "beta_notebook_id": beta_notebook.id,
        "beta_cell_id": beta_cell.id,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client, {**ids, **{key: build_headers(key) for key in headers}}

    app.dependency_overrides.clear()
    cell_agent_runtime.root_dir = original_runtime_root
    await engine.dispose()


@pytest.mark.asyncio
async def test_notebooks_are_scoped_to_workspace(enterprise_client):
    client, context = enterprise_client

    create_alpha = await client.post(
        "/api/notebooks",
        json={"title": "Alpha Notebook", "description": "Tenant scoped"},
        headers=context["admin_alpha"],
    )
    assert create_alpha.status_code == 201

    create_beta = await client.post(
        "/api/notebooks",
        json={"title": "Beta Notebook 2", "description": "Tenant scoped"},
        headers=context["admin_beta"],
    )
    assert create_beta.status_code == 201
    beta_notebook_id = create_beta.json()["id"]

    alpha_list = await client.get("/api/notebooks", headers=context["admin_alpha"])
    assert alpha_list.status_code == 200
    assert [item["title"] for item in alpha_list.json()] == ["Alpha Notebook"]

    beta_list = await client.get("/api/notebooks", headers=context["admin_beta"])
    assert beta_list.status_code == 200
    assert {item["title"] for item in beta_list.json()} == {"Beta Notebook", "Beta Notebook 2"}

    cross_workspace_get = await client.get(
        f"/api/notebooks/{beta_notebook_id}",
        headers=context["admin_alpha"],
    )
    assert cross_workspace_get.status_code == 404


@pytest.mark.asyncio
async def test_direct_cell_access_is_blocked_across_workspaces(enterprise_client):
    client, context = enterprise_client

    response = await client.put(
        f"/api/cells/{context['beta_cell_id']}",
        json={"source": "select 2"},
        headers=context["admin_alpha"],
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_audit_events_require_admin_and_capture_mutations(enterprise_client):
    client, context = enterprise_client

    create_notebook = await client.post(
        "/api/notebooks",
        json={"title": "Audited Notebook"},
        headers=context["admin_alpha"],
    )
    assert create_notebook.status_code == 201

    admin_audit = await client.get(
        "/api/enterprise/audit-events",
        headers=context["admin_alpha"],
    )
    assert admin_audit.status_code == 200
    actions = [event["action"] for event in admin_audit.json()]
    assert "notebook.create" in actions

    analyst_audit = await client.get(
        "/api/enterprise/audit-events",
        headers=context["analyst_alpha"],
    )
    assert analyst_audit.status_code == 403


async def _create_notebook(
    client: AsyncClient,
    headers: dict[str, str],
    title: str,
) -> dict:
    response = await client.post(
        "/api/notebooks",
        json={"title": title, "description": "Runtime validation notebook"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def _create_cell(
    client: AsyncClient,
    headers: dict[str, str],
    notebook_id: str,
    cell_type: str,
    source: str,
    position: int,
) -> dict:
    response = await client.post(
        f"/api/notebooks/{notebook_id}/cells",
        json={
            "cell_type": cell_type,
            "source": source,
            "position": position,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _parse_sse_events(payload: str) -> list[dict[str, object]]:
    events = []
    for block in payload.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", maxsplit=1)[1].strip()
            elif line.startswith("data:"):
                data += line.split(":", maxsplit=1)[1].strip()
        events.append({"event": event_name, "data": json.loads(data) if data else {}})
    return events


@pytest.mark.asyncio
async def test_cells_execute_with_runtime_dependencies(enterprise_client):
    client, context = enterprise_client
    notebook = await _create_notebook(client, context["admin_alpha"], "Runtime Demo")

    sql_cell = await _create_cell(
        client,
        context["admin_alpha"],
        notebook["id"],
        "sql",
        "\n".join(
            [
                "-- output: sales_summary",
                "SELECT * FROM (VALUES",
                "  ('Laptop', 10),",
                "  ('Mouse', 5)",
                ") AS sales_summary(product_name, revenue);",
            ]
        ),
        0,
    )
    python_cell = await _create_cell(
        client,
        context["admin_alpha"],
        notebook["id"],
        "python",
        "\n".join(
            [
                "product_metrics = sales_summary.assign(",
                '    double_revenue=sales_summary["revenue"] * 2,',
                ")",
            ]
        ),
        1,
    )
    sql_from_python_cell = await _create_cell(
        client,
        context["admin_alpha"],
        notebook["id"],
        "sql",
        "\n".join(
            [
                "-- output: premium_products",
                "SELECT product_name, double_revenue",
                "FROM product_metrics",
                "WHERE double_revenue >= 10",
                "ORDER BY double_revenue DESC;",
            ]
        ),
        2,
    )
    chart_cell = await _create_cell(
        client,
        context["admin_alpha"],
        notebook["id"],
        "chart",
        json.dumps(
            {
                "data_source": "premium_products",
                "chart_type": "bar",
                "x_field": "product_name",
                "y_field": "double_revenue",
            }
        ),
        3,
    )
    markdown_cell = await _create_cell(
        client,
        context["admin_alpha"],
        notebook["id"],
        "markdown",
        "\n".join(
            [
                "Rows: {{ premium_products.row_count }}",
                "Columns: {{ premium_products.columns }}",
                "Preview: {{ premium_products.preview }}",
            ]
        ),
        4,
    )

    chart_execute = await client.post(
        f"/api/cells/{chart_cell['id']}/execute",
        headers=context["admin_alpha"],
    )
    assert chart_execute.status_code == 200
    chart_body = chart_execute.json()
    assert chart_body["status"] == "success"
    assert chart_body["output"]["chart"]["data_source"] == "premium_products"

    executed_cells = {
        item["cell_id"]: item["output"] for item in chart_body["executed_cells"]
    }
    assert executed_cells[sql_cell["id"]]["row_count"] == 2
    assert executed_cells[python_cell["id"]]["data"]["variable"] == "product_metrics"
    assert executed_cells[sql_from_python_cell["id"]]["row_count"] == 2
    assert executed_cells[chart_cell["id"]]["agent"]["mode"] == "stateless-dag-file-ipc"

    chart_workspace = Path(chart_body["output"]["agent"]["workspace_dir"])
    assert (chart_workspace / "task.json").exists()
    assert (chart_workspace / "context.json").exists()
    assert (chart_workspace / "inbox").exists()
    sql_workspace = Path(executed_cells[sql_from_python_cell["id"]]["agent"]["workspace_dir"])
    assert list((sql_workspace / "outbox").glob("to-*.json"))

    markdown_execute = await client.post(
        f"/api/cells/{markdown_cell['id']}/execute",
        headers=context["admin_alpha"],
    )
    assert markdown_execute.status_code == 200
    markdown_output = markdown_execute.json()["output"]
    assert markdown_output["status"] == "success"
    assert "Rows: 2" in markdown_output["html"]
    assert "double_revenue" in markdown_output["html"]

    notebook_state = await client.get(
        f"/api/notebooks/{notebook['id']}",
        headers=context["admin_alpha"],
    )
    assert notebook_state.status_code == 200
    notebook_cells = {item["id"]: item for item in notebook_state.json()["cells"]}
    assert notebook_cells[sql_from_python_cell["id"]]["output"]["row_count"] == 2
    assert notebook_cells[chart_cell["id"]]["output"]["agent"]["published_messages"] >= 0


@pytest.mark.asyncio
async def test_chart_execution_returns_structured_errors(enterprise_client):
    client, context = enterprise_client
    notebook = await _create_notebook(client, context["admin_alpha"], "Chart Error Demo")
    chart_cell = await _create_cell(
        client,
        context["admin_alpha"],
        notebook["id"],
        "chart",
        json.dumps({"data_source": "missing_table", "chart_type": "bar"}),
        0,
    )

    response = await client.post(
        f"/api/cells/{chart_cell['id']}/execute",
        headers=context["admin_alpha"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert "missing_table" in body["output"]["error"]


@pytest.mark.asyncio
async def test_ai_edit_streams_progress_and_sanitized_content(
    enterprise_client,
    monkeypatch,
):
    client, context = enterprise_client
    notebook = await _create_notebook(client, context["admin_alpha"], "AI Edit Demo")
    chart_cell = await _create_cell(
        client,
        context["admin_alpha"],
        notebook["id"],
        "chart",
        json.dumps({"data_source": "sales_summary", "chart_type": "bar"}),
        0,
    )

    async def fake_stream(**kwargs):
        del kwargs
        yield "```json\n{\n"
        yield '  "data_source": "sales_summary",\n'
        yield '  "chart_type": "line"\n}\n```'

    monkeypatch.setattr(llm_client, "stream", fake_stream)

    response = await client.post(
        f"/api/cells/{chart_cell['id']}/edit-with-ai",
        json={"prompt": "Switch the chart to a line chart."},
        headers=context["admin_alpha"],
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_events(response.text)
    progress_stages = [
        event["data"]["stage"]
        for event in events
        if event["event"] == "progress"
    ]
    assert progress_stages[:4] == ["context", "dag", "ipc", "rewrite"]
    assert "validate" in progress_stages
    done_event = next(event for event in events if event["event"] == "done")
    assert done_event["data"]["progress"] == 1.0
    assert done_event["data"]["details"]["mode"] == "stateless-dag-file-ipc"

    content = done_event["data"]["content"]
    parsed = json.loads(content)
    assert parsed["data_source"] == "sales_summary"
    assert parsed["chart_type"] == "line"
    assert "```" not in content


def test_ai_edit_normalization_preserves_cell_contracts():
    sql_result = _normalize_ai_edit_output(
        CellType.SQL,
        "-- output: sales_summary\nSELECT * FROM sales;",
        "```sql\nSELECT product_name FROM sales;\n```",
    )
    assert sql_result.startswith("-- output: sales_summary")

    chart_result = json.loads(
        _normalize_ai_edit_output(
            CellType.CHART,
            json.dumps({"data_source": "sales_summary", "chart_type": "bar"}),
            json.dumps({"chart_type": "line"}),
        )
    )
    assert chart_result["data_source"] == "sales_summary"
    assert chart_result["chart_type"] == "line"

    markdown_result = _normalize_ai_edit_output(
        CellType.MARKDOWN,
        "Rows: {{ sales_summary.row_count }}",
        "```markdown\n## Summary\nRows: {{ sales_summary.row_count }}\n```",
    )
    assert markdown_result.startswith("## Summary")

    python_result = _normalize_ai_edit_output(
        CellType.PYTHON,
        "result = sales_summary.copy()",
        "```python\ntransformed = sales_summary.copy()\n```",
    )
    assert "transformed" in python_result

    with pytest.raises(SyntaxError):
        _normalize_ai_edit_output(CellType.PYTHON, "", "for")


def test_dependency_dag_uses_latest_previous_definition_only():
    dag = CellDependencyDAG()
    dag.build(
        [
            {"id": "cell-1", "cell_type": "python", "source": "print(result)", "position": 0},
            {"id": "cell-2", "cell_type": "python", "source": "result = 1", "position": 1},
            {"id": "cell-3", "cell_type": "python", "source": "next_value = result + 1", "position": 2},
            {"id": "cell-4", "cell_type": "python", "source": "result = 5", "position": 3},
            {"id": "cell-5", "cell_type": "python", "source": "final_value = result + 2", "position": 4},
        ]
    )

    assert dag.get_direct_dependencies("cell-1") == []
    assert dag.get_direct_dependencies("cell-3") == ["cell-2"]
    assert dag.get_direct_dependencies("cell-5") == ["cell-4"]
    assert dag.get_execution_plan("cell-5") == ["cell-4", "cell-5"]


def test_build_table_catalog_only_publishes_materialized_python_outputs():
    bundle = build_runtime_bundle(
        [
            SimpleNamespace(
                id="py-cell-1",
                cell_type="python",
                source=(
                    "import pandas as pd\n"
                    "sales_summary = pd.DataFrame({'revenue': [10, 5]})\n"
                ),
                output={
                    "status": "success",
                    "data": {
                        "variable": "sales_summary",
                        "columns": ["revenue"],
                        "rows": [[10], [5]],
                    },
                },
                position=0,
            )
        ]
    )

    tables = build_table_catalog(bundle.ordered_cells)
    assert list(tables) == ["sales_summary"]
    assert "pd" not in tables


def test_build_table_catalog_accepts_retrieved_cell_context_shape():
    tables = build_table_catalog(
        [
            {
                "cell_id": "sql-cell-1",
                "cell_type": "sql",
                "source": "-- output: sales_summary\nSELECT 1 AS revenue",
                "output": {
                    "status": "success",
                    "columns": ["revenue"],
                    "rows": [[1]],
                    "row_count": 1,
                },
            }
        ]
    )

    assert "sales_summary" in tables
    assert tables["sales_summary"]["rows"] == [[1]]


@pytest.mark.asyncio
async def test_proxy_agent_materializes_sql_results_for_downstream_agents(monkeypatch):
    observed: dict[str, object] = {}

    class FakeSQLAgent:
        async def execute(self, query: str, context=None) -> InformationUnit:
            observed["sql_context"] = context or {}
            return InformationUnit(
                role="SQL Agent",
                action="generate_sql_query",
                description="Stub SQL result",
                content="SELECT 1 AS total",
            )

    class FakeChartAgent:
        async def execute(self, query: str, context=None) -> InformationUnit:
            observed["chart_context"] = context or {}
            return InformationUnit(
                role="Chart Agent",
                action="generate_chart",
                description="Stub chart result",
                content={"data_source": "sql_result", "chart_type": "bar"},
            )

    agent = ProxyAgent()

    async def fake_plan(query: str, context: dict[str, object]) -> dict[str, object]:
        del query, context
        return {
            "agents": ["sql_agent", "chart_agent"],
            "execution_plan": [
                {"agent": "sql_agent", "depends_on": [], "description": "Get data"},
                {
                    "agent": "chart_agent",
                    "depends_on": ["sql_agent"],
                    "description": "Chart data",
                },
            ],
        }

    monkeypatch.setitem(AGENT_REGISTRY, "sql_agent", FakeSQLAgent())
    monkeypatch.setitem(AGENT_REGISTRY, "chart_agent", FakeChartAgent())
    monkeypatch.setattr(agent, "_create_execution_plan", fake_plan)

    result = await agent.execute("Show me the total as a chart", {})
    assert result.action == "orchestrate_agents"

    chart_context = observed["chart_context"]
    predecessor_info = chart_context["predecessor_info"]
    assert predecessor_info
    assert predecessor_info[0].role == "SQL Agent"
    assert predecessor_info[0].content["query"] == "SELECT 1 AS total"
    assert predecessor_info[0].content["result"]["rows"] == [[1]]

    results = result.content["results"]
    assert results[0]["output"]["rows"] == [[1]]
