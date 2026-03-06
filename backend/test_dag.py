import asyncio
from app.context.dag import CellDependencyDAG

dag = CellDependencyDAG()
dag.build([
  {"id": "cell1", "cell_type": "python", "source": "x = 1", "position": 0},
  {"id": "cell2", "cell_type": "python", "source": "y = x + 1", "position": 1},
  {"id": "cell3", "cell_type": "python", "source": "z = y + x", "position": 2},
  {"id": "cell4", "cell_type": "python", "source": "x = 5", "position": 3},
  {"id": "cell5", "cell_type": "python", "source": "w = x + 1", "position": 4},
])
print(dag.to_dict())
print("Exec plan for cell5:", dag.get_execution_plan("cell5"))
print("Exec plan for cell3:", dag.get_execution_plan("cell3"))
