"""Function calling / tool definitions for LLM agents."""

from __future__ import annotations

EXECUTE_SQL_TOOL = {
    "type": "function",
    "function": {
        "name": "execute_sql",
        "description": "Execute a SQL query against the connected database and return results",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The SQL query to execute",
                },
            },
            "required": ["query"],
        },
    },
}

EXECUTE_PYTHON_TOOL = {
    "type": "function",
    "function": {
        "name": "execute_python",
        "description": "Execute Python code in a sandboxed environment",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to execute",
                },
            },
            "required": ["code"],
        },
    },
}

GENERATE_CHART_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_chart",
        "description": "Generate an ECharts specification for data visualization",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "heatmap", "area"],
                    "description": "Type of chart to generate",
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
                },
                "spec": {
                    "type": "object",
                    "description": "ECharts option specification",
                },
            },
            "required": ["chart_type", "spec"],
        },
    },
}

CREATE_CELL_TOOL = {
    "type": "function",
    "function": {
        "name": "create_cell",
        "description": "Create a new cell in the notebook",
        "parameters": {
            "type": "object",
            "properties": {
                "cell_type": {
                    "type": "string",
                    "enum": ["sql", "python", "chart", "markdown"],
                    "description": "Type of cell to create",
                },
                "source": {
                    "type": "string",
                    "description": "Content/code for the cell",
                },
            },
            "required": ["cell_type", "source"],
        },
    },
}
