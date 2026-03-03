"""Context Retrieval - Adaptive context selection based on cell dependency DAG.

Supports:
- Cell-level queries: traverse ancestors
- Notebook-level queries: traverse descendants from data source cell
- Task-type-based pruning
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.communication.info_unit import InformationUnit
from app.communication.shared_buffer import SharedBuffer
from app.context.dag import CellDependencyDAG

logger = logging.getLogger(__name__)

TASK_CELL_TYPES = {
    "nl2sql": {"sql"},
    "nl2dscode": {"python"},
    "nl2vis": {"chart", "python", "sql"},
    "nl2insight": {"python", "sql", "markdown"},
    "eda": {"python"},
    "cleaning": {"python"},
    "report": {"markdown", "python", "sql"},
    "general": {"sql", "python", "chart", "markdown"},
}


class ContextRetriever:
    """Retrieves relevant cell contexts from the DAG for agent queries."""

    def __init__(self, dag: CellDependencyDAG, buffer: Optional[SharedBuffer] = None):
        self.dag = dag
        self.buffer = buffer

    def retrieve_cell_context(
        self,
        cell_id: str,
        task_type: str = "general",
        cells_data: Optional[dict[str, dict]] = None,
    ) -> list[dict[str, Any]]:
        """Cell-level query: get ancestor cells as context."""
        ancestor_ids = self.dag.get_ancestors(cell_id)
        ancestor_ids.add(cell_id)

        allowed_types = TASK_CELL_TYPES.get(task_type, TASK_CELL_TYPES["general"])

        relevant_cells = []
        for cid in ancestor_ids:
            node = self.dag.get_node(cid)
            if node and node.cell_type in allowed_types:
                cell_info: dict[str, Any] = {
                    "cell_id": cid,
                    "cell_type": node.cell_type,
                    "variables_defined": list(node.variables_defined),
                }
                if cells_data and cid in cells_data:
                    cell_info["source"] = cells_data[cid].get("source", "")
                    cell_info["output"] = cells_data[cid].get("output")
                relevant_cells.append(cell_info)

        if self.buffer:
            for cell_info in relevant_cells:
                info_units = self._get_cell_info_units(cell_info["cell_id"])
                if info_units:
                    cell_info["info_units"] = [u.to_dict() for u in info_units]

        return relevant_cells

    def retrieve_notebook_context(
        self,
        data_variable: Optional[str] = None,
        task_type: str = "general",
        cells_data: Optional[dict[str, dict]] = None,
    ) -> list[dict[str, Any]]:
        """Notebook-level query: find data source cell and get descendants."""
        if data_variable:
            source_cell_id = None
            for cell_id in self.dag._nodes:
                node = self.dag.get_node(cell_id)
                if node and data_variable in node.variables_defined:
                    source_cell_id = cell_id
                    break

            if source_cell_id:
                descendant_ids = self.dag.get_descendants(source_cell_id)
                descendant_ids.add(source_cell_id)
            else:
                descendant_ids = set(self.dag._nodes.keys())
        else:
            descendant_ids = set(self.dag._nodes.keys())

        allowed_types = TASK_CELL_TYPES.get(task_type, TASK_CELL_TYPES["general"])

        relevant_cells = []
        for cid in descendant_ids:
            node = self.dag.get_node(cid)
            if node and node.cell_type in allowed_types:
                cell_info: dict[str, Any] = {
                    "cell_id": cid,
                    "cell_type": node.cell_type,
                    "variables_defined": list(node.variables_defined),
                }
                if cells_data and cid in cells_data:
                    cell_info["source"] = cells_data[cid].get("source", "")
                    cell_info["output"] = cells_data[cid].get("output")
                relevant_cells.append(cell_info)

        return relevant_cells

    def _get_cell_info_units(self, cell_id: str) -> list[InformationUnit]:
        """Get info units associated with a cell from the shared buffer."""
        if not self.buffer:
            return []
        all_units = self.buffer.retrieve_all()
        return [u for u in all_units if u.cell_id == cell_id]
