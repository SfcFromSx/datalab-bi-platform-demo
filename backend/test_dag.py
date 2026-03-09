from app.context.dag import CellDependencyDAG
from app.context.tracker import variable_tracker

def test_dag_with_unexecuted_python_cell():
    dag = CellDependencyDAG()
    # Simulate first cell having been executed and producing output data
    cells = [
        {
            "id": "cell-sql",
            "cell_type": "sql",
            "source": "-- output: sales_summary\\nSELECT *",
            "position": 0,
            "output": {"data": {"variable": "sales_summary"}}
        },
        {
            "id": "cell-python-1",
            "cell_type": "python",
            "source": "df = sales_summary.copy()\\nenriched = df",
            "position": 1,
            # Output represents a previously executed cell
            "output": {"data": {"variable": "enriched"}, "exports": {"df": {}, "enriched": {}}}
        },
        {
            "id": "cell-python-new",
            "cell_type": "python",
            "source": "y = df + 1",
            "position": 2,
        }
    ]
    dag.build(cells)
    
    # cell-python-new references 'df'. Does it map to 'cell-python-1'?
    node = dag.get_node("cell-python-new")
    print(f"Node referenced: {node.variables_referenced}")
    print(f"Node ancestors: {node.ancestors}")
    assert "cell-python-1" in node.ancestors

if __name__ == "__main__":
    test_dag_with_unexecuted_python_cell()
