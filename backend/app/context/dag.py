"""Cell Dependency DAG - Directed Acyclic Graph of cell dependencies.

Implements Algorithm 3 from the DataLab paper:
1. Identify new variables in each cell
2. Find referenced cells for each cell
3. Construct the dependency DAG
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.context.tracker import variable_tracker

logger = logging.getLogger(__name__)


@dataclass
class DAGNode:
    cell_id: str
    cell_type: str
    position: int
    variables_defined: set[str] = field(default_factory=set)
    variables_referenced: set[str] = field(default_factory=set)
    ancestors: set[str] = field(default_factory=set)
    descendants: set[str] = field(default_factory=set)


class CellDependencyDAG:
    """Manages the directed acyclic graph of cell dependencies."""

    def __init__(self):
        self._nodes: dict[str, DAGNode] = {}
        self._var_to_cell: dict[str, str] = {}
        self._cell_order: list[str] = []
        self._cells_snapshot: list[dict] = []

    def build(self, cells: list[dict]) -> None:
        self._nodes.clear()
        self._var_to_cell.clear()
        self._cell_order.clear()
        ordered_cells = sorted(cells, key=lambda item: item.get("position", 0))
        self._cells_snapshot = [dict(cell) for cell in ordered_cells]

        latest_definitions: dict[str, str] = {}
        for cell in ordered_cells:
            cell_id = cell["id"]
            cell_type = cell["cell_type"]
            source = cell.get("source", "")
            position = cell.get("position", 0)

            cv = variable_tracker.analyze_cell(cell_id, cell_type, source)
            node = DAGNode(
                cell_id=cell_id,
                cell_type=cell_type,
                position=position,
                variables_defined=cv.defined,
                variables_referenced=cv.referenced,
            )

            for ref_var in sorted(cv.referenced):
                defining_cell = latest_definitions.get(ref_var)
                if defining_cell and defining_cell != cell_id:
                    node.ancestors.add(defining_cell)
                    self._nodes[defining_cell].descendants.add(cell_id)

            self._nodes[cell_id] = node
            self._cell_order.append(cell_id)

            for var in sorted(cv.defined):
                latest_definitions[var] = cell_id

        self._var_to_cell = latest_definitions.copy()

    def update_cell(self, cell_id: str, cell_type: str, source: str) -> None:
        updated = False
        for cell in self._cells_snapshot:
            if cell["id"] == cell_id:
                cell["cell_type"] = cell_type
                cell["source"] = source
                updated = True
                break
        if not updated:
            self._cells_snapshot.append(
                {
                    "id": cell_id,
                    "cell_type": cell_type,
                    "source": source,
                    "position": len(self._cells_snapshot),
                }
            )
        self.build(self._cells_snapshot)

    def remove_cell(self, cell_id: str) -> None:
        self._cells_snapshot = [
            cell for cell in self._cells_snapshot if cell["id"] != cell_id
        ]
        self.build(self._cells_snapshot)

    def get_ancestors(self, cell_id: str) -> set[str]:
        visited: set[str] = set()
        stack = [cell_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            node = self._nodes.get(current)
            if node:
                for anc in node.ancestors:
                    if anc not in visited:
                        stack.append(anc)
        visited.discard(cell_id)
        return visited

    def get_descendants(self, cell_id: str) -> set[str]:
        visited: set[str] = set()
        stack = [cell_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            node = self._nodes.get(current)
            if node:
                for desc in node.descendants:
                    if desc not in visited:
                        stack.append(desc)
        visited.discard(cell_id)
        return visited

    def get_node(self, cell_id: str) -> Optional[DAGNode]:
        return self._nodes.get(cell_id)

    def get_direct_dependencies(self, cell_id: str) -> list[str]:
        node = self._nodes.get(cell_id)
        if not node:
            return []
        return sorted(
            node.ancestors,
            key=lambda dependency_id: self._nodes[dependency_id].position,
        )

    def get_direct_descendants(self, cell_id: str) -> list[str]:
        node = self._nodes.get(cell_id)
        if not node:
            return []
        return sorted(
            node.descendants,
            key=lambda dependency_id: self._nodes[dependency_id].position,
        )

    def get_execution_plan(self, cell_id: str) -> list[str]:
        active_cells = self.get_ancestors(cell_id)
        active_cells.add(cell_id)
        return [candidate for candidate in self._cell_order if candidate in active_cells]

    def to_dict(self) -> dict:
        return {
            cell_id: {
                "cell_type": node.cell_type,
                "position": node.position,
                "defined": list(node.variables_defined),
                "referenced": list(node.variables_referenced),
                "ancestors": list(node.ancestors),
                "descendants": list(node.descendants),
            }
            for cell_id, node in self._nodes.items()
        }
