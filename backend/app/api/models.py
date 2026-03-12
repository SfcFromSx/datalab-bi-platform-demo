"""LLM model listing and switching endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.llm.client import llm_client

router = APIRouter(tags=["models"])


class ModelInfo(BaseModel):
    id: str
    name: str
    model: str
    active: bool


class ModelListResponse(BaseModel):
    models: list[ModelInfo]
    active_id: str


class SetActiveModelRequest(BaseModel):
    id: str


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    presets = settings.get_model_presets()
    active = llm_client.active_preset_id
    return ModelListResponse(
        models=[
            ModelInfo(
                id=p["id"],
                name=p.get("name", p["model"]),
                model=p["model"],
                active=p["id"] == active,
            )
            for p in presets
        ],
        active_id=active,
    )


@router.post("/models/active", response_model=ModelListResponse)
async def set_active_model(data: SetActiveModelRequest):
    try:
        llm_client.set_model(data.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return await list_models()
