"""WebSocket handler for real-time notebook cell execution."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import async_session_factory
from app.execution.cell_runtime import CellRuntime
from app.models import Cell, DataSource, Notebook

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
cell_runtime = CellRuntime()


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

    await websocket.send_text(json.dumps({
        "type": "cell_update",
        "payload": {"cell_id": cell_id, "status": "running"},
    }))

    try:
        async with async_session_factory() as session:
            cell = await session.get(Cell, cell_id)
            if not cell:
                raise ValueError(f"Cell {cell_id} not found")

            notebook_cells_result = await session.execute(
                select(Cell)
                .where(Cell.notebook_id == notebook_id)
                .order_by(Cell.position)
            )
            notebook_cells = notebook_cells_result.scalars().all()

            datasource_result = await session.execute(select(DataSource))
            workspace_datasources = datasource_result.scalars().all()

            source_overrides = {cell_id: source} if source else None
            execution_result = await cell_runtime.execute_target(
                notebook_cells,
                cell_id,
                source_overrides=source_overrides,
                datasources=workspace_datasources,
            )

            for notebook_cell in notebook_cells:
                if notebook_cell.id in execution_result.outputs_by_id:
                    notebook_cell.output = execution_result.outputs_by_id[notebook_cell.id]

            await session.flush()

        for executed_id, output in execution_result.outputs_by_id.items():
            await manager.broadcast(notebook_id, {
                "type": "cell_update",
                "payload": {
                    "cell_id": executed_id,
                    "status": output.get("status", "error"),
                    "output": output,
                },
            })
    except Exception as e:
        logger.error(f"Cell execution error: {e}")
        await manager.broadcast(notebook_id, {
            "type": "cell_update",
            "payload": {
                "cell_id": cell_id,
                "status": "error",
                "output": {"status": "error", "error": str(e)},
            },
        })
