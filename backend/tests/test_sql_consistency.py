import pytest
from app.agents.chatbi_agent import ChatBIAgent
from app.execution.sql_executor import sql_executor

@pytest.mark.asyncio
async def test_agent_can_see_upstream_tables(monkeypatch):
    # Setup: simulate a table created in a previous cell
    # In a real notebook, this would be in the 'raw_tables' of the context
    context = {
        "raw_tables": {
            "sales_summary": {
                "columns": ["product", "revenue"],
                "rows": [["Laptop", 1000], ["Mouse", 50]]
            }
        },
        "datasources": [],
        "datasource_id": None
    }
    
    agent = ChatBIAgent()
    
    # We mock _generate_sql_stream to return a query that uses sales_summary
    async def fake_generate_sql_stream(query, context):
        # The query passed to _generate_sql_stream is the base_prompt
        assert "sales_summary" in query
        yield "SELECT * FROM sales_summary ORDER BY revenue DESC LIMIT 1"

    monkeypatch.setattr(agent, "_generate_sql_stream", fake_generate_sql_stream)
    
    # Execute
    result = await agent.execute("What is the top product in sales_summary?", context)
    
    # Verify
    assert result.action == "chat_bi_response"
    assert "Laptop" in result.content["message"]
    assert "1000" in result.content["message"]
    assert "SELECT * FROM sales_summary" in result.content["message"]

@pytest.mark.asyncio
async def test_agent_can_see_multiple_datasources(monkeypatch):
    # Setup: simulate two datasources
    from app.models.datasource import DataSource, DataSourceType
    
    ds1 = DataSource(id="ds-1", name="sales", ds_type=DataSourceType.CSV, connection_string="/tmp/sales.csv")
    ds2 = DataSource(id="ds-2", name="inventory", ds_type=DataSourceType.CSV, connection_string="/tmp/inv.csv")
    
    context = {
        "raw_tables": {},
        "datasources": [ds1, ds2],
        "datasource_id": "ds-1" # currently focused on ds-1
    }
    
    # Mock sql_executor._import_datasource to actually register some tables
    def fake_import(conn, datasource):
        if datasource.id == "ds-1":
            conn.execute("CREATE TABLE sales (id INT)")
        else:
            conn.execute("CREATE TABLE inventory (id INT)")
            
    monkeypatch.setattr(sql_executor, "_import_datasource", fake_import)
    
    agent = ChatBIAgent()
    
    async def fake_generate_sql_stream(query, context):
        yield "SELECT s.id FROM sales s JOIN inventory i ON s.id = i.id"

    monkeypatch.setattr(agent, "_generate_sql_stream", fake_generate_sql_stream)
    
    # Execute - this should not raise "Table sales / inventory not found"
    result = await agent.execute("join sales and inventory", context)
    
    assert result.action == "chat_bi_response"
    assert "SELECT s.id FROM sales s JOIN inventory i" in result.content["message"]
