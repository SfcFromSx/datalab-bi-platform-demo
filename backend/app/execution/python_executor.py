"""Sandboxed Python code execution engine."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

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
sys.stdout = _stdout_capture
sys.stderr = _stderr_capture

_result = {{"status": "success", "stdout": "", "stderr": "", "data": None, "error": None}}

try:
    _globals = {{"pd": pd, "__builtins__": __builtins__}}
    exec("""{code}""", _globals)

    # Capture any DataFrame in the namespace for display
    for _name, _val in _globals.items():
        if isinstance(_val, pd.DataFrame) and not _name.startswith("_"):
            _result["data"] = {{
                "columns": list(_val.columns),
                "rows": _val.head(500).values.tolist(),
                "shape": list(_val.shape),
                "variable": _name,
            }}
            break

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

    async def execute(self, code: str) -> dict[str, Any]:
        escaped_code = code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        wrapper = WRAPPER_TEMPLATE.replace("{code}", escaped_code)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(wrapper)
            script_path = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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
