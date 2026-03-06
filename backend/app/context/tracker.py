"""Variable Tracker - Tracks variables defined and referenced across notebook cells.

For Python cells: Uses AST to find global variable definitions and external references.
For SQL cells: Tracks SELECT output as a data variable.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CellVariables:
    """Variables defined and referenced by a single cell."""

    cell_id: str
    cell_type: str
    defined: set[str] = field(default_factory=set)
    referenced: set[str] = field(default_factory=set)


class VariableTracker:
    """Track variable definitions and references across notebook cells."""

    def analyze_cell(self, cell_id: str, cell_type: str, source: str) -> CellVariables:
        if cell_type == "python":
            return self._analyze_python(cell_id, source)
        if cell_type == "sql":
            return self._analyze_sql(cell_id, source)
        if cell_type == "chart":
            return self._analyze_chart(cell_id, source)
        if cell_type == "markdown":
            return self._analyze_markdown(cell_id, source)
        return CellVariables(cell_id=cell_id, cell_type=cell_type)

    def _analyze_python(self, cell_id: str, source: str) -> CellVariables:
        """Parse Python AST to find global variable definitions and external references."""
        result = CellVariables(cell_id=cell_id, cell_type="python")

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return result

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result.defined.add(node.name)
            elif isinstance(node, ast.ClassDef):
                result.defined.add(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    result.defined.add(name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    result.defined.add(name)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        result.defined.add(target.id)
                    elif isinstance(target, ast.Tuple):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                result.defined.add(elt.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                result.defined.add(node.target.id)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                result.defined.add(node.target.id)
                result.referenced.add(node.target.id)

        all_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                all_names.add(node.id)

        if isinstance(__builtins__, dict):
            builtins_set = set(dir(__builtins__))
        else:
            builtins_set = set(dir(__builtins__))
        result.referenced = all_names - result.defined - builtins_set

        return result

    def _analyze_sql(self, cell_id: str, source: str) -> CellVariables:
        """Track SQL SELECT output and table references."""
        result = CellVariables(cell_id=cell_id, cell_type="sql")

        output_match = re.search(r'--\s*output:\s*(\w+)', source, re.IGNORECASE)
        if output_match:
            result.defined.add(output_match.group(1))
        else:
            result.defined.add(f"sql_result_{cell_id[:8]}")

        table_pattern = r'(?:FROM|JOIN)\s+["\']?(\w+)["\']?'
        tables = re.findall(table_pattern, source, re.IGNORECASE)
        for table in tables:
            if table.lower() not in ("select", "where", "group", "order", "having"):
                result.referenced.add(table)

        return result

    def _analyze_chart(self, cell_id: str, source: str) -> CellVariables:
        """Chart cells reference a data variable."""
        result = CellVariables(cell_id=cell_id, cell_type="chart")

        try:
            spec = json.loads(source)
        except json.JSONDecodeError:
            spec = None

        if isinstance(spec, dict):
            for key in ("data_source", "source_variable"):
                value = spec.get(key)
                if isinstance(value, str) and value:
                    result.referenced.add(value)

            dataset = spec.get("dataset")
            if isinstance(dataset, dict):
                variable = dataset.get("sourceVariable")
                if isinstance(variable, str) and variable:
                    result.referenced.add(variable)

        data_match = re.search(r'data[_-]?source\s*[:=]\s*["\']?(\w+)', source, re.IGNORECASE)
        if data_match:
            result.referenced.add(data_match.group(1))

        return result

    def _analyze_markdown(self, cell_id: str, source: str) -> CellVariables:
        """Markdown cells can reference notebook variables via handlebars-style placeholders."""
        result = CellVariables(cell_id=cell_id, cell_type="markdown")
        placeholders = re.findall(r"{{\s*([\w.]+)\s*}}", source)
        for placeholder in placeholders:
            result.referenced.add(placeholder.split(".", maxsplit=1)[0])

        return result


variable_tracker = VariableTracker()
