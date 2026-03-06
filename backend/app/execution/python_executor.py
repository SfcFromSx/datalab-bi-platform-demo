"""Sandboxed Python code execution engine."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def _resolve_python_executable() -> str:
    backend_root = Path(__file__).resolve().parents[2]
    candidates = [
        backend_root / ".venv" / "bin" / "python",
        backend_root / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable

WRAPPER_TEMPLATE = '''
import sys
import json
import io
import pandas as pd
import traceback

_stdout_capture = io.StringIO()
_stderr_capture = io.StringIO()
_old_stdout = sys.stdout
_old_stderr = sys.stderr

_result = {{"status": "success", "stdout": "", "stderr": "", "data": None, "error": None}}
_bootstrap_tables = {bootstrap_tables}
_bootstrap_code = {bootstrap_code}
_user_code = {code}

try:
    _globals = {{"pd": pd, "__builtins__": __builtins__}}
    for _name, _table in _bootstrap_tables.items():
        _globals[_name] = pd.DataFrame(
            _table.get("rows", []),
            columns=_table.get("columns", []),
        )

    if _bootstrap_code.strip():
        _bootstrap_stdout = io.StringIO()
        _bootstrap_stderr = io.StringIO()
        sys.stdout = _bootstrap_stdout
        sys.stderr = _bootstrap_stderr
        exec(_bootstrap_code, _globals)

    _known_keys = set(_globals.keys())

    sys.stdout = _stdout_capture
    sys.stderr = _stderr_capture
    exec(_user_code, _globals)

    _dataframes = []
    for _name, _val in _globals.items():
        if isinstance(_val, pd.DataFrame) and not _name.startswith("_"):
            _dataframes.append((_name, _val))

    _new_frames = [item for item in _dataframes if item[0] not in _known_keys]
    _selected = _new_frames[-1] if _new_frames else (_dataframes[-1] if _dataframes else None)
    if _selected:
        _frame_name, _frame = _selected
        _result["data"] = {{
            "columns": list(_frame.columns),
            "rows": _frame.head(500).values.tolist(),
            "shape": list(_frame.shape),
            "variable": _frame_name,
        }}

except Exception as _e:
    _result["status"] = "error"
    _result["error"] = traceback.format_exc()

sys.stdout = _old_stdout
sys.stderr = _old_stderr
_result["stdout"] = _stdout_capture.getvalue()
_result["stderr"] = _stderr_capture.getvalue()

print("__RESULT_JSON__")
print(json.dumps(_result, default=str))
'''


class PythonExecutor:
    """Execute Python code in a subprocess sandbox with timeout and resource limits."""

    def __init__(self):
        self.timeout = settings.sandbox_timeout
        self.python_executable = _resolve_python_executable()

    async def execute(
        self,
        code: str,
        bootstrap_code: str = "",
        bootstrap_tables: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        wrapper = WRAPPER_TEMPLATE.format(
            code=json.dumps(code),
            bootstrap_code=json.dumps(bootstrap_code),
            bootstrap_tables=json.dumps(bootstrap_tables or {}),
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(wrapper)
            script_path = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                self.python_executable,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONNOUSERSITE": "1"},
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "status": "error",
                    "stdout": "",
                    "stderr": "",
                    "data": None,
                    "error": f"Execution timed out after {self.timeout}s",
                }

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            marker = "__RESULT_JSON__"
            if marker in stdout:
                json_str = stdout.split(marker, 1)[1].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            return {
                "status": "error" if process.returncode != 0 else "success",
                "stdout": stdout,
                "stderr": stderr,
                "data": None,
                "error": stderr if process.returncode != 0 else None,
            }
        finally:
            Path(script_path).unlink(missing_ok=True)


python_executor = PythonExecutor()
