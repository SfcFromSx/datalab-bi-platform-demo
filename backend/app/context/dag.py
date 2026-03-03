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
    variables_defined: set[str] = field(default_factory=set)
    variables_referenced: set[str] = field(default_factory=set)
    ancestors: set[str] = field(default_factory=set)
    descendants: set[str] = field(default_factory=set)


class CellDependencyDAG:
    """Manages the directed acyclic graph of cell dependencies."""

    def __init__(self):
        self._nodes: dict[str, DAGNode] = {}
        self._var_to_cell: dict[str, str] = {}

    def build(self, cells: list[dict]) -> None:
        self._nodes.clear()
        self._var_to_cell.clear()

        for cell in cells:
            cell_id = cell["id"]
            cell_type = cell["cell_type"]
            source = cell.get("source", "")

            cv = variable_tracker.analyze_cell(cell_id, cell_type, source)
            node = DAGNode(
                cell_id=cell_id,
                cell_type=cell_type,
                variables_defined=cv.defined,
                variables_referenced=cv.referenced,
            )
            self._nodes[cell_id] = node

            for var in cv.defined:
                self._var_to_cell[var] = cell_id

        for cell_id, node in self._nodes.items():
            for ref_var in node.variables_referenced:
                defining_cell = self._var_to_cell.get(ref_var)
                if defining_cell and defining_cell != cell_id:
                    node.ancestors.add(defining_cell)
                    self._nodes[defining_cell].descendants.add(cell_id)

    def update_cell(self, cell_id: str, cell_type: str, source: str) -> None:
        if cell_id in self._nodes:
            old_node = self._nodes[cell_id]
            for anc in old_node.ancestors:
                if anc in self._nodes:
                    self._nodes[anc].descendants.discard(cell_id)
            for desc in old_node.descendants:
                if desc in self._nodes:
                    self._nodes[desc].ancestors.discard(cell_id)
            for var, cid in list(self._var_to_cell.items()):
                if cid == cell_id:
                    del self._var_to_cell[var]

        cv = variable_tracker.analyze_cell(cell_id, cell_type, source)
        node = DAGNode(
            cell_id=cell_id,
            cell_type=cell_type,
            variables_defined=cv.defined,
            variables_referenced=cv.referenced,
        )
        self._nodes[cell_id] = node

        for var in cv.defined:
            self._var_to_cell[var] = cell_id

        for ref_var in node.variables_referenced:
            defining_cell = self._var_to_cell.get(ref_var)
            if defining_cell and defining_cell != cell_id:
                node.ancestors.add(defining_cell)
                self._nodes[defining_cell].descendants.add(cell_id)

    def remove_cell(self, cell_id: str) -> None:
        if cell_id not in self._nodes:
            return
        node = self._nodes[cell_id]
        for anc in node.ancestors:
            if anc in self._nodes:
                self._nodes[anc].descendants.discard(cell_id)
        for desc in node.descendants:
            if desc in self._nodes:
                self._nodes[desc].ancestors.discard(cell_id)
        for var, cid in list(self._var_to_cell.items()):
            if cid == cell_id:
                del self._var_to_cell[var]
        del self._nodes[cell_id]

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

    def to_dict(self) -> dict:
        return {
            cell_id: {
                "cell_type": node.cell_type,
                "defined": list(node.variables_defined),
                "referenced": list(node.variables_referenced),
                "ancestors": list(node.ancestors),
                "descendants": list(node.descendants),
            }
            for cell_id, node in self._nodes.items()
        }
