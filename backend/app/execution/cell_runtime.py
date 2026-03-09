from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from app.config import settings
from app.execution import execution_sandbox, python_executor, sql_executor
from app.models.cell import CellType
from app.models.datasource import DataSource
from app.notebook_runtime import (
    NotebookRuntimeBundle,
    build_runtime_bundle,
    build_table_catalog,
    build_value_catalog,
    extract_output_values,
    summarize_output,
)

FILE_EXTENSIONS = {
    "sql": ".sql",
    "python": ".py",
    "chart": ".json",
    "markdown": ".md",
}


@dataclass
class CellPaths:
    workspace_dir: Path
    agent_file: Path
    source_file: Path
    task_file: Path
    task_markdown_file: Path
    context_file: Path
    bootstrap_file: Path
    output_file: Path
    inbox_dir: Path
    outbox_dir: Path


@dataclass
class CellRuntimePlan:
    bundle: NotebookRuntimeBundle
    plan: list[str]
    paths_by_id: dict[str, CellPaths]


@dataclass
class CellRuntimeSessionResult:
    run_id: str
    plan: list[str]
    outputs_by_id: dict[str, dict[str, Any]]
    paths_by_id: dict[str, CellPaths]


class CellRuntime:
    def __init__(self, root_dir: Path | None = None):
        self.root_dir = Path(root_dir) if root_dir else settings.data_dir / "cell_runtime"
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def build_plan(
        self,
        cells: Iterable[Any],
        target_cell_id: str,
        source_overrides: dict[str, str] | None = None,
    ) -> CellRuntimePlan:
        prepared_cells = self._prepare_cells(cells, source_overrides)
        bundle = build_runtime_bundle(prepared_cells)
        if target_cell_id not in bundle.cells_by_id:
            raise ValueError(f"Unknown cell runtime '{target_cell_id}'")

        plan = bundle.dag.get_execution_plan(target_cell_id)
        paths_by_id = {
            cell_id: self._paths_for_cell(bundle.cells_by_id[cell_id])
            for cell_id in plan
        }
        return CellRuntimePlan(
            bundle=bundle,
            plan=plan,
            paths_by_id=paths_by_id,
        )

    async def execute_target(
        self,
        cells: Iterable[Any],
        target_cell_id: str,
        source_overrides: dict[str, str] | None = None,
        datasources: Sequence[DataSource] | None = None,
    ) -> CellRuntimeSessionResult:
        plan = self.build_plan(
            cells,
            target_cell_id,
            source_overrides=source_overrides,
        )
        run_id = uuid.uuid4().hex
        outputs_by_id: dict[str, dict[str, Any]] = {}
        active_cells = set(plan.plan)
        datasource_ids = [datasource.id for datasource in datasources or []]

        for cell_id in plan.plan:
            self._prepare_workspace(
                plan.bundle.cells_by_id[cell_id],
                plan.paths_by_id[cell_id],
            )

        for cell_id in plan.plan:
            cell = plan.bundle.cells_by_id[cell_id]
            paths = plan.paths_by_id[cell_id]

            dependencies = plan.bundle.dag.get_direct_dependencies(cell_id)
            ancestors_set = set(plan.bundle.dag.get_ancestors(cell_id))
            ancestors = [
                candidate
                for candidate in plan.plan
                if candidate != cell_id and candidate in ancestors_set
            ]
            inbox_messages = self._read_inbox(paths.inbox_dir)
            tables = self._load_tables(plan, cell_id)
            values = self._load_values(plan, cell_id)
            bootstrap_code = self._build_python_bootstrap(plan, cell_id, tables, values)
            fingerprint = self._fingerprint(plan, cell_id)

            task_payload = {
                "mode": "stateless-dag-file-ipc",
                "run_id": run_id,
                "cell_id": cell_id,
                "cell_type": cell["cell_type"],
                "dependencies": dependencies,
                "ancestors": ancestors,
                "plan": plan.plan,
                "fingerprint": fingerprint,
            }
            context_payload = {
                "dependencies": dependencies,
                "ancestors": ancestors,
                "inbox_messages": inbox_messages,
                "table_catalog": tables,
                "value_catalog": values,
                "bootstrap_sources": self._bootstrap_sources(plan, cell_id, tables, values),
            }

            self._write_json(paths.task_file, task_payload)
            self._write_json(paths.context_file, context_payload)
            self._write_text(paths.task_markdown_file, self._task_markdown(cell, task_payload))
            if bootstrap_code:
                self._write_text(paths.bootstrap_file, bootstrap_code)
            else:
                paths.bootstrap_file.unlink(missing_ok=True)

            raw_output = await self._execute_cell(
                cell,
                tables=tables,
                values=values,
                bootstrap_code=bootstrap_code,
                datasource_ids=datasource_ids,
                datasources=datasources or [],
            )
            published_messages = self._publish_messages(
                plan,
                cell_id,
                raw_output,
                fingerprint,
                active_cells,
            )
            runtime_info = {
                "mode": "stateless-dag-file-ipc",
                "run_id": run_id,
                "workspace_dir": str(paths.workspace_dir),
                "source_file": str(paths.source_file),
                "task_file": str(paths.task_file),
                "context_file": str(paths.context_file),
                "bootstrap_file": str(paths.bootstrap_file) if bootstrap_code else None,
                "output_file": str(paths.output_file),
                "inbox_dir": str(paths.inbox_dir),
                "outbox_dir": str(paths.outbox_dir),
                "dependencies": dependencies,
                "ancestors": ancestors,
                "plan": plan.plan,
                "fingerprint": fingerprint,
                "input_messages": len(inbox_messages),
                "published_messages": published_messages,
            }
            output = {**raw_output, "agent": runtime_info}
            self._write_json(paths.output_file, output)
            outputs_by_id[cell_id] = output

        return CellRuntimeSessionResult(
            run_id=run_id,
            plan=plan.plan,
            outputs_by_id=outputs_by_id,
            paths_by_id=plan.paths_by_id,
        )

    def describe_cell(
        self,
        cells: Iterable[Any],
        target_cell_id: str,
        source_overrides: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        prepared_cells = self._prepare_cells(cells, source_overrides)
        
        # Find the target cell and its position in the sorted list
        # We assume the input 'cells' is already sorted or we sort it here to be safe
        sorted_cells = sorted(prepared_cells, key=lambda c: c.get("position", 0))
        
        target_index = -1
        for i, cell in enumerate(sorted_cells):
            if cell["id"] == target_cell_id:
                target_index = i
                break
        
        if target_index == -1:
            # Fallback to DAG if cell not found in the list (shouldn't happen)
            plan = self.build_plan(cells, target_cell_id, source_overrides=source_overrides)
            ancestors = [cell_id for cell_id in plan.plan if cell_id != target_cell_id]
            dependencies = plan.bundle.dag.get_direct_dependencies(target_cell_id)
            workspace_dir = str(plan.paths_by_id[target_cell_id].workspace_dir)
            source_file = str(plan.paths_by_id[target_cell_id].source_file)
            task_file = str(plan.paths_by_id[target_cell_id].task_file)
            context_file = str(plan.paths_by_id[target_cell_id].context_file)
            plan_list = plan.plan
        else:
            # Linear ancestors: all cells before the target in the sorted list
            ancestors = [c["id"] for c in sorted_cells[:target_index]]
            
            # Still build the plan to get workspace paths and DAG dependencies
            plan = self.build_plan(cells, target_cell_id, source_overrides=source_overrides)
            paths = plan.paths_by_id[target_cell_id]
            workspace_dir = str(paths.workspace_dir)
            source_file = str(paths.source_file)
            task_file = str(paths.task_file)
            context_file = str(paths.context_file)
            dependencies = plan.bundle.dag.get_direct_dependencies(target_cell_id)
            plan_list = plan.plan

        return {
            "mode": "stateless-dag-file-ipc",
            "cell_id": target_cell_id,
            "workspace_dir": workspace_dir,
            "source_file": source_file,
            "task_file": task_file,
            "context_file": context_file,
            "dependencies": dependencies,
            "ancestors": ancestors,
            "plan": plan_list,
        }

    def write_edit_task(
        self,
        cells: Iterable[Any],
        target_cell_id: str,
        prompt: str,
        source_overrides: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        plan = self.build_plan(
            cells,
            target_cell_id,
            source_overrides=source_overrides,
        )
        cell = plan.bundle.cells_by_id[target_cell_id]
        paths = plan.paths_by_id[target_cell_id]
        self._prepare_workspace(cell, paths)
        edit_task_file = paths.workspace_dir / "ai-edit-task.json"
        edit_context_file = paths.workspace_dir / "ai-edit-context.json"
        payload = {
            "mode": "stateless-dag-file-ipc",
            "cell_id": target_cell_id,
            "prompt": prompt,
            "dependencies": plan.bundle.dag.get_direct_dependencies(target_cell_id),
            "ancestors": [cell_id for cell_id in plan.plan if cell_id != target_cell_id],
            "plan": plan.plan,
        }
        self._write_json(edit_task_file, payload)
        self._write_json(
            edit_context_file,
            {
                "workspace_dir": str(paths.workspace_dir),
                "source_file": str(paths.source_file),
                "task_file": str(paths.task_file),
                "dependencies": payload["dependencies"],
                "ancestors": payload["ancestors"],
                "plan": payload["plan"],
            },
        )
        return {
            **payload,
            "workspace_dir": str(paths.workspace_dir),
            "task_file": str(edit_task_file),
            "context_file": str(edit_context_file),
        }

    def _prepare_cells(
        self,
        cells: Iterable[Any],
        source_overrides: dict[str, str] | None,
    ) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []
        for cell in cells:
            metadata = getattr(cell, "metadata_", None)
            cell_type = getattr(cell, "cell_type", "")
            if hasattr(cell_type, "value"):
                cell_type = cell_type.value
            cell_id = getattr(cell, "id")
            prepared.append(
                {
                    "id": cell_id,
                    "notebook_id": getattr(cell, "notebook_id", None),
                    "cell_type": cell_type,
                    "source": (
                        source_overrides.get(cell_id, getattr(cell, "source", ""))
                        if source_overrides
                        else getattr(cell, "source", "")
                    ),
                    "output": getattr(cell, "output", None),
                    "position": getattr(cell, "position", 0),
                    "metadata": metadata,
                }
            )
        return prepared

    def _paths_for_cell(self, cell: dict[str, Any]) -> CellPaths:
        workspace_name = (
            f"{int(cell.get('position', 0)):03d}-"
            f"{cell.get('cell_type', 'cell')}-"
            f"{str(cell.get('id', 'cell'))[:8]}"
        )
        workspace_dir = (
            self.root_dir
            / self._safe_segment(cell.get("notebook_id") or "notebook")
            / workspace_name
        )
        extension = FILE_EXTENSIONS.get(cell.get("cell_type", ""), ".txt")
        return CellPaths(
            workspace_dir=workspace_dir,
            agent_file=workspace_dir / "agent.json",
            source_file=workspace_dir / f"source{extension}",
            task_file=workspace_dir / "task.json",
            task_markdown_file=workspace_dir / "task.md",
            context_file=workspace_dir / "context.json",
            bootstrap_file=workspace_dir / "bootstrap.py",
            output_file=workspace_dir / "output.json",
            inbox_dir=workspace_dir / "inbox",
            outbox_dir=workspace_dir / "outbox",
        )

    def _prepare_workspace(self, cell: dict[str, Any], paths: CellPaths) -> None:
        paths.workspace_dir.mkdir(parents=True, exist_ok=True)
        for directory in (paths.inbox_dir, paths.outbox_dir):
            shutil.rmtree(directory, ignore_errors=True)
            directory.mkdir(parents=True, exist_ok=True)
        self._write_json(
            paths.agent_file,
            {
                "cell_id": cell["id"],
                "cell_type": cell["cell_type"],
                "notebook_id": cell.get("notebook_id"),
                "position": cell.get("position", 0),
            },
        )
        self._write_text(paths.source_file, cell.get("source", ""))

    def _load_tables(self, plan: CellRuntimePlan, cell_id: str) -> dict[str, dict[str, Any]]:
        return build_table_catalog(self._load_artifact_cells(plan, cell_id))

    def _load_values(self, plan: CellRuntimePlan, cell_id: str) -> dict[str, Any]:
        return build_value_catalog(self._load_artifact_cells(plan, cell_id))

    def _load_artifact_cells(
        self,
        plan: CellRuntimePlan,
        cell_id: str,
    ) -> list[dict[str, Any]]:
        cells: list[dict[str, Any]] = []
        for ancestor_id in plan.bundle.dag.get_execution_plan(cell_id):
            if ancestor_id == cell_id:
                continue
            paths = plan.paths_by_id.get(ancestor_id)
            if not paths or not paths.output_file.exists():
                continue
            output = self._read_json(paths.output_file)
            if not isinstance(output, dict):
                continue
            cells.append(
                {
                    "id": ancestor_id,
                    "cell_type": plan.bundle.cells_by_id[ancestor_id]["cell_type"],
                    "source": plan.bundle.cells_by_id[ancestor_id].get("source", ""),
                    "output": output,
                }
            )
        return cells

    def _build_python_bootstrap(
        self,
        plan: CellRuntimePlan,
        cell_id: str,
        tables: dict[str, dict[str, Any]],
        values: dict[str, Any],
    ) -> str:
        code_parts: list[str] = []
        for ancestor_id in self._select_python_bootstrap_cell_ids(plan, cell_id, tables, values):
            source_file = plan.paths_by_id[ancestor_id].source_file
            if source_file.exists():
                code_parts.append(source_file.read_text(encoding="utf-8"))
        return "\n\n".join(part for part in code_parts if part.strip())

    def _select_python_bootstrap_cell_ids(
        self,
        plan: CellRuntimePlan,
        cell_id: str,
        tables: dict[str, dict[str, Any]],
        values: dict[str, Any],
    ) -> list[str]:
        target_node = plan.bundle.dag.get_node(cell_id)
        if not target_node:
            return []

        available_names = set(tables) | set(values)
        required_names = {
            name
            for name in target_node.variables_referenced
            if name not in available_names
        }
        if not required_names:
            return []

        selected_ids: list[str] = []
        for ancestor_id in reversed(plan.bundle.dag.get_execution_plan(cell_id)):
            if ancestor_id == cell_id:
                continue
            cell = plan.bundle.cells_by_id[ancestor_id]
            if cell.get("cell_type") != "python":
                continue
            node = plan.bundle.dag.get_node(ancestor_id)
            if not node or not (node.variables_defined & required_names):
                continue
            selected_ids.append(ancestor_id)
            available_names |= node.variables_defined
            required_names |= {
                name for name in node.variables_referenced if name not in available_names
            }

        selected_ids.reverse()
        return selected_ids

    def _bootstrap_sources(
        self,
        plan: CellRuntimePlan,
        cell_id: str,
        tables: dict[str, dict[str, Any]],
        values: dict[str, Any],
    ) -> list[str]:
        return [
            str(plan.paths_by_id[ancestor_id].source_file)
            for ancestor_id in self._select_python_bootstrap_cell_ids(
                plan,
                cell_id,
                tables,
                values,
            )
        ]

    async def _execute_cell(
        self,
        cell: dict[str, Any],
        tables: dict[str, dict[str, Any]],
        values: dict[str, Any],
        bootstrap_code: str,
        datasource_ids: Sequence[str],
        datasources: Sequence[DataSource],
    ) -> dict[str, Any]:
        cell_type = CellType(cell["cell_type"])
        source = cell.get("source", "")

        if cell_type == CellType.PYTHON:
            return await python_executor.execute(
                source,
                bootstrap_code=bootstrap_code,
                bootstrap_tables=tables,
                bootstrap_values=values,
            )

        if cell_type == CellType.SQL:
            return sql_executor.execute_isolated(
                source,
                tables=tables,
                datasource_ids=datasource_ids,
                datasources=datasources,
            )

        if cell_type == CellType.CHART:
            chart_result = self._execute_chart_cell(source, tables)
            return chart_result

        if cell_type == CellType.MARKDOWN:
            resolved_markdown = self._render_markdown_placeholders(source, tables, values)
            markdown_output = await execution_sandbox.execute(cell_type, resolved_markdown)
            markdown_output["bindings"] = sorted(set(tables) | set(values))
            return markdown_output

        return await execution_sandbox.execute(cell_type, source)

    def _execute_chart_cell(
        self,
        source: str,
        tables: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            spec = json.loads(source)
        except json.JSONDecodeError as exc:
            return {
                "status": "error",
                "error": f"Chart cells must contain valid JSON: {exc}",
            }

        if not isinstance(spec, dict):
            return {"status": "error", "error": "Chart cell JSON must be an object"}

        data_source = self._resolve_chart_data_source(spec)
        if data_source and data_source not in tables:
            return {
                "status": "error",
                "error": f"Chart data source '{data_source}' was not found in notebook outputs",
            }

        table = tables.get(data_source) if data_source else None
        return {
            "status": "success",
            "error": None,
            "chart": {
                "data_source": data_source,
                "columns": table.get("columns", []) if table else [],
                "row_count": len(table.get("rows", [])) if table else 0,
            },
        }

    def _publish_messages(
        self,
        plan: CellRuntimePlan,
        cell_id: str,
        output: dict[str, Any],
        fingerprint: str,
        active_cells: set[str],
    ) -> int:
        paths = plan.paths_by_id[cell_id]
        descendants = [
            descendant_id
            for descendant_id in plan.bundle.dag.get_direct_descendants(cell_id)
            if descendant_id in active_cells
        ]
        payload = self._message_payload(plan, cell_id, output, fingerprint)
        count = 0
        for descendant_id in descendants:
            outbound = {**payload, "to_cell_id": descendant_id}
            self._write_json(paths.outbox_dir / f"to-{descendant_id}.json", outbound)
            self._write_json(
                plan.paths_by_id[descendant_id].inbox_dir / f"from-{cell_id}.json",
                outbound,
            )
            count += 1
        return count

    def _message_payload(
        self,
        plan: CellRuntimePlan,
        cell_id: str,
        output: dict[str, Any],
        fingerprint: str,
    ) -> dict[str, Any]:
        cell = plan.bundle.cells_by_id[cell_id]
        tables = build_table_catalog([{**cell, "output": output}])
        values = extract_output_values({**cell, "output": output})
        return {
            "message_id": uuid.uuid4().hex,
            "from_cell_id": cell_id,
            "cell_type": cell["cell_type"],
            "fingerprint": fingerprint,
            "variables_defined": sorted(set(tables) | set(values)),
            "summary": summarize_output(output),
            "source_file": str(plan.paths_by_id[cell_id].source_file),
            "output_file": str(plan.paths_by_id[cell_id].output_file),
            "tables": tables,
            "values": values,
        }

    def _read_inbox(self, inbox_dir: Path) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for message_file in sorted(inbox_dir.glob("*.json")):
            if message_file.name.startswith("._"):
                continue
            payload = self._read_json(message_file)
            if isinstance(payload, dict):
                messages.append(payload)
        return messages

    def _fingerprint(self, plan: CellRuntimePlan, cell_id: str) -> str:
        cell = plan.bundle.cells_by_id[cell_id]
        payload = {
            "cell_id": cell_id,
            "cell_type": cell["cell_type"],
            "source": cell.get("source", ""),
            "dependencies": [],
        }
        for dependency_id in plan.bundle.dag.get_direct_dependencies(cell_id):
            paths = plan.paths_by_id.get(dependency_id)
            if not paths or not paths.output_file.exists():
                continue
            dependency_output = self._read_json(paths.output_file)
            payload["dependencies"].append(
                {
                    "cell_id": dependency_id,
                    "summary": summarize_output(dependency_output),
                }
            )
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    def _task_markdown(self, cell: dict[str, Any], payload: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"# Cell Runtime {cell['id']}",
                "",
                f"- Type: {cell['cell_type']}",
                f"- Mode: {payload['mode']}",
                f"- Run: {payload['run_id']}",
                f"- Dependencies: {', '.join(payload['dependencies']) or 'none'}",
                f"- Ancestors: {', '.join(payload['ancestors']) or 'none'}",
                "",
                "## Source",
                "",
                "```",
                cell.get("source", ""),
                "```",
                ]
        )

    @staticmethod
    def _render_markdown_placeholders(
        source: str,
        tables: dict[str, dict[str, Any]],
        values: dict[str, Any] | None = None,
    ) -> str:
        scalar_values = values or {}

        def replace(match: re.Match[str]) -> str:
            expr = match.group(1).strip()
            variable_name, _, attribute = expr.partition(".")
            table = tables.get(variable_name)
            if table:
                if attribute == "row_count":
                    return str(len(table.get("rows", [])))
                if attribute == "columns":
                    return ", ".join(str(column) for column in table.get("columns", []))
                if attribute == "preview":
                    return json.dumps(table.get("rows", [])[:3], default=str)
                if attribute:
                    return match.group(0)
                return json.dumps(table, default=str)

            if variable_name not in scalar_values:
                return match.group(0)

            value = scalar_values[variable_name]
            if not attribute or attribute == "value":
                return CellRuntime._stringify_markdown_value(value)

            resolved_value = CellRuntime._resolve_value_attribute(value, attribute)
            if resolved_value is _MISSING:
                return match.group(0)
            return CellRuntime._stringify_markdown_value(resolved_value)

        return re.sub(r"{{\s*([^}]+)\s*}}", replace, source)

    @staticmethod
    def _resolve_chart_data_source(spec: dict[str, Any]) -> str | None:
        for key in ("data_source", "source_variable"):
            value = spec.get(key)
            if isinstance(value, str) and value:
                return value
        dataset = spec.get("dataset")
        if isinstance(dataset, dict):
            value = dataset.get("sourceVariable")
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _safe_segment(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")
        return cleaned or "workspace"

    @staticmethod
    def _resolve_value_attribute(value: Any, attribute: str) -> Any:
        current = value
        for part in attribute.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
                continue
            return _MISSING
        return current

    @staticmethod
    def _stringify_markdown_value(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)) or value is None:
            return str(value)
        return json.dumps(value, default=str)

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def _write_text(path: Path, payload: str) -> None:
        path.write_text(payload, encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


cell_runtime = CellRuntime()


_MISSING = object()
