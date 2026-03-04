from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DataLab backend...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down DataLab backend...")


app = FastAPI(
    title="DataLab",
    description="Unified LLM-Powered BI Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import agents, cells, datasources, folders, knowledge, notebooks, websocket  # noqa: E402

app.include_router(notebooks.router, prefix="/api")
app.include_router(cells.router, prefix="/api")
app.include_router(folders.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(datasources.router, prefix="/api")
app.include_router(websocket.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
