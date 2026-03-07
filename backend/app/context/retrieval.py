"""Context Retrieval - Adaptive context selection based on cell dependency DAG.

Supports:
- Cell-level queries: traverse ancestors
- Notebook-level queries: traverse descendants from data source cell
- Task-type-based pruning
"""

from __future__ import annotations

import logging
import re
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
        return self._collect_cells(ancestor_ids, allowed_types, cells_data)

    def retrieve_notebook_context(
        self,
        data_variable: Optional[str] = None,
        task_type: str = "general",
        cells_data: Optional[dict[str, dict]] = None,
    ) -> list[dict[str, Any]]:
        """Notebook-level query: find data source cell and get descendants."""
        if data_variable:
            source_cell_id = self._find_source_cell_id(data_variable)
            if source_cell_id:
                descendant_ids = self.dag.get_descendants(source_cell_id)
                descendant_ids.add(source_cell_id)
            else:
                descendant_ids = set(self.dag._nodes.keys())
        else:
            descendant_ids = set(self.dag._nodes.keys())

        allowed_types = TASK_CELL_TYPES.get(task_type, TASK_CELL_TYPES["general"])
        return self._collect_cells(descendant_ids, allowed_types, cells_data)

    def retrieve_query_context(
        self,
        query: str,
        focus_cell_id: Optional[str] = None,
        task_type: str = "general",
        cells_data: Optional[dict[str, dict]] = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        """Retrieve the most relevant notebook cells for a natural-language query."""
        allowed_types = TASK_CELL_TYPES.get(task_type, TASK_CELL_TYPES["general"])
        query_tokens = self._tokenize(query)
        candidate_ids: set[str] = set()

        if focus_cell_id:
            candidate_ids.update(self.dag.get_ancestors(focus_cell_id))
            candidate_ids.add(focus_cell_id)
            candidate_ids.update(self.dag.get_descendants(focus_cell_id))

        scored: list[tuple[float, dict[str, Any]]] = []
        for cell_id, node in self.dag._nodes.items():
            if node.cell_type not in allowed_types:
                continue

            score = 0.0
            if cell_id in candidate_ids:
                score += 5.0

            score += self._score_node(node, query_tokens)

            if cells_data and cell_id in cells_data:
                source = cells_data[cell_id].get("source", "")
                output = cells_data[cell_id].get("output")
                score += self._score_text(source, query_tokens)
                score += self._score_text(self._summarize_output(output), query_tokens)

            if score <= 0:
                continue

            cell_info = self._build_cell_info(cell_id, node, cells_data)
            scored.append((score, cell_info))

        if not scored:
            fallback_ids = {
                cell_id
                for cell_id, node in self.dag._nodes.items()
                if node.cell_type in allowed_types
            }
            scored = [
                (0.0, self._build_cell_info(cell_id, self.dag.get_node(cell_id), cells_data))
                for cell_id in self._ordered_cell_ids(fallback_ids, cells_data)[-limit:]
                if self.dag.get_node(cell_id)
            ]

        scored.sort(
            key=lambda item: (
                -item[0],
                self._cell_position(item[1]["cell_id"], cells_data),
                item[1]["cell_id"],
            )
        )

        results = [item[1] for item in scored[:limit]]
        results.sort(
            key=lambda item: (
                self._cell_position(item["cell_id"], cells_data),
                item["cell_id"],
            )
        )
        return results

    def _build_cell_info(
        self,
        cell_id: str,
        node,
        cells_data: Optional[dict[str, dict]] = None,
    ) -> dict[str, Any]:
        cell_info: dict[str, Any] = {
            "cell_id": cell_id,
            "cell_type": node.cell_type,
            "variables_defined": sorted(node.variables_defined),
            "variables_referenced": sorted(node.variables_referenced),
        }
        if cells_data and cell_id in cells_data:
            cell_info["source"] = cells_data[cell_id].get("source", "")
            cell_info["output"] = cells_data[cell_id].get("output")
            cell_info["position"] = cells_data[cell_id].get("position", 0)
        if self.buffer:
            info_units = self._get_cell_info_units(cell_id)
            if info_units:
                cell_info["info_units"] = [u.to_dict() for u in info_units]
        return cell_info

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if token}

    def _score_node(self, node, query_tokens: set[str]) -> float:
        tokens = (
            {token.lower() for token in node.variables_defined}
            | {token.lower() for token in node.variables_referenced}
        )
        return float(len(tokens & query_tokens))

    def _score_text(self, text: str, query_tokens: set[str]) -> float:
        if not text:
            return 0.0
        text_tokens = self._tokenize(text)
        return float(len(text_tokens & query_tokens))

    @staticmethod
    def _summarize_output(output: Any) -> str:
        if not output:
            return ""
        if isinstance(output, dict):
            parts: list[str] = []
            if output.get("error"):
                parts.append(str(output["error"]))
            if output.get("stdout"):
                parts.append(str(output["stdout"]))
            if output.get("columns"):
                parts.extend(str(col) for col in output["columns"])
            if output.get("data") and isinstance(output["data"], dict):
                parts.extend(str(col) for col in output["data"].get("columns", []))
            return " ".join(parts)
        return str(output)

    def _get_cell_info_units(self, cell_id: str) -> list[InformationUnit]:
        """Get info units associated with a cell from the shared buffer."""
        if not self.buffer:
            return []
        all_units = self.buffer.retrieve_all()
        return [u for u in all_units if u.cell_id == cell_id]

    def _collect_cells(
        self,
        cell_ids: set[str],
        allowed_types: set[str],
        cells_data: Optional[dict[str, dict]] = None,
    ) -> list[dict[str, Any]]:
        relevant_cells: list[dict[str, Any]] = []
        for cell_id in self._ordered_cell_ids(cell_ids, cells_data):
            node = self.dag.get_node(cell_id)
            if node and node.cell_type in allowed_types:
                relevant_cells.append(self._build_cell_info(cell_id, node, cells_data))
        return relevant_cells

    def _ordered_cell_ids(
        self,
        cell_ids: set[str],
        cells_data: Optional[dict[str, dict]] = None,
    ) -> list[str]:
        return sorted(
            cell_ids,
            key=lambda cell_id: (self._cell_position(cell_id, cells_data), cell_id),
        )

    def _cell_position(
        self,
        cell_id: str,
        cells_data: Optional[dict[str, dict]] = None,
    ) -> int:
        if cells_data and cell_id in cells_data:
            return cells_data[cell_id].get("position", 0)
        node = self.dag.get_node(cell_id)
        return node.position if node else 0

    def _find_source_cell_id(self, data_variable: str) -> str | None:
        for cell_id, node in self.dag._nodes.items():
            if data_variable in node.variables_defined:
                return cell_id
        return None
