"""WebSocket handler for real-time notebook updates."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.agents import proxy_agent
from app.agents.context_builder import load_notebook_query_context
from app.database import async_session_factory
from app.execution import execution_sandbox
from app.models import Notebook
from app.models.cell import CellType

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections per notebook."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, notebook_id: str):
        await websocket.accept()
        if notebook_id not in self.active_connections:
            self.active_connections[notebook_id] = []
        self.active_connections[notebook_id].append(websocket)
        logger.info(f"WebSocket connected for notebook {notebook_id}")

    def disconnect(self, websocket: WebSocket, notebook_id: str):
        if notebook_id in self.active_connections:
            self.active_connections[notebook_id].remove(websocket)
            if not self.active_connections[notebook_id]:
                del self.active_connections[notebook_id]

    async def broadcast(self, notebook_id: str, message: dict[str, Any]):
        if notebook_id in self.active_connections:
            text = json.dumps(message, default=str)
            for connection in self.active_connections[notebook_id]:
                try:
                    await connection.send_text(text)
                except Exception:
                    pass


manager = ConnectionManager()


@router.websocket("/ws/{notebook_id}")
async def websocket_endpoint(websocket: WebSocket, notebook_id: str):
    try:
        async with async_session_factory() as session:
            notebook = await session.scalar(
                select(Notebook).where(
                    Notebook.id == notebook_id,
                )
            )
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")
    except HTTPException:
        await websocket.accept()
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, notebook_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "cell_execute":
                await _handle_cell_execute(websocket, notebook_id, message)
            elif msg_type == "agent_query":
                await _handle_agent_query(websocket, notebook_id, message)
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": f"Unknown type: {msg_type}"})
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket, notebook_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, notebook_id)


async def _handle_cell_execute(
    websocket: WebSocket, notebook_id: str, message: dict
):
    payload = message.get("payload", {})
    cell_id = payload.get("cell_id", "")
    source = payload.get("source", "")
    cell_type_str = payload.get("cell_type", "python")

    try:
        cell_type = CellType(cell_type_str)
    except ValueError:
        cell_type = CellType.PYTHON

    await websocket.send_text(json.dumps({
        "type": "cell_update",
        "payload": {"cell_id": cell_id, "status": "running"},
    }))

    output = await execution_sandbox.execute(cell_type, source)

    await manager.broadcast(notebook_id, {
        "type": "cell_update",
        "payload": {
            "cell_id": cell_id,
            "status": output.get("status", "error"),
            "output": output,
        },
    })


async def _handle_agent_query(
    websocket: WebSocket, notebook_id: str, message: dict
):
    payload = message.get("payload", {})
    query = payload.get("query", "")
    datasource_id = payload.get("datasource_id")
    cell_id = payload.get("cell_id")
    task_id = str(uuid.uuid4())

    try:
        await websocket.send_text(json.dumps({
            "type": "agent_progress",
            "payload": {
                "task_id": task_id,
                "status": "running",
                "message": "Thinking...",
            },
        }))

        async with async_session_factory() as session:
            agent_context = await load_notebook_query_context(
                session,
                notebook_id,
                query,
                focus_cell_id=cell_id,
                datasource_id=datasource_id,
            )

        result = await proxy_agent.execute(query, agent_context)

        content = result.content
        agent_msg = "Task completed successfully"
        if isinstance(content, dict) and "message" in content:
            agent_msg = content["message"]

        await manager.broadcast(notebook_id, {
            "type": "agent_complete",
            "payload": {
                "task_id": task_id,
                "status": "completed",
                "cells_created": [],
                "message": agent_msg,
            },
        })
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "agent_progress",
            "payload": {
                "task_id": task_id,
                "status": "error",
                "message": str(e),
            },
        }))
