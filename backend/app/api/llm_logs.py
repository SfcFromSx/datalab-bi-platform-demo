"""LLM log API – browse and inspect all recorded LLM calls."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.llm_log import LLMLog
from app.schemas.llm_log import LLMLogListResponse, LLMLogResponse, LLMLogStatsResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["llm-logs"])


@router.get("/llm-logs/stats", response_model=LLMLogStatsResponse)
async def get_llm_log_stats(
    session: AsyncSession = Depends(get_session),
):
    """Aggregated statistics for all LLM calls."""
    result = await session.execute(
        select(
            func.count(LLMLog.id).label("total"),
            func.sum(case((LLMLog.status == "success", 1), else_=0)).label("success"),
            func.sum(case((LLMLog.status == "error", 1), else_=0)).label("errors"),
            func.coalesce(func.sum(LLMLog.tokens_prompt), 0).label("prompt_tokens"),
            func.coalesce(func.sum(LLMLog.tokens_completion), 0).label("completion_tokens"),
            func.coalesce(func.avg(LLMLog.duration_ms), 0).label("avg_duration"),
        )
    )
    row = result.one()

    # Per-feature counts
    feat_result = await session.execute(
        select(LLMLog.feature, func.count(LLMLog.id)).group_by(LLMLog.feature)
    )
    by_feature = {f: c for f, c in feat_result.all()}

    # Per-model counts
    model_result = await session.execute(
        select(LLMLog.model, func.count(LLMLog.id)).group_by(LLMLog.model)
    )
    by_model = {m: c for m, c in model_result.all()}

    return LLMLogStatsResponse(
        total_calls=row.total or 0,
        success_count=row.success or 0,
        error_count=row.errors or 0,
        total_prompt_tokens=row.prompt_tokens or 0,
        total_completion_tokens=row.completion_tokens or 0,
        avg_duration_ms=round(float(row.avg_duration or 0), 1),
        by_feature=by_feature,
        by_model=by_model,
    )


@router.get("/llm-logs", response_model=LLMLogListResponse)
async def list_llm_logs(
    feature: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List LLM call logs with optional filtering."""
    q = select(LLMLog)
    count_q = select(func.count(LLMLog.id))

    if feature:
        q = q.where(LLMLog.feature == feature)
        count_q = count_q.where(LLMLog.feature == feature)
    if status:
        q = q.where(LLMLog.status == status)
        count_q = count_q.where(LLMLog.status == status)

    total = (await session.execute(count_q)).scalar() or 0

    q = q.order_by(LLMLog.created_at.desc()).offset(offset).limit(limit)
    rows = (await session.execute(q)).scalars().all()

    # Return list items WITHOUT full messages/response to keep payload small
    logs = []
    for r in rows:
        log = LLMLogResponse.model_validate(r)
        # Truncate messages and response for list view
        if log.messages:
            for msg in log.messages:
                if isinstance(msg.get("content"), str) and len(msg["content"]) > 200:
                    msg["content"] = msg["content"][:200] + "..."
        if log.response and len(log.response) > 300:
            log.response = log.response[:300] + "..."
        logs.append(log)

    return LLMLogListResponse(logs=logs, total=total)


@router.get("/llm-logs/{log_id}", response_model=LLMLogResponse)
async def get_llm_log(
    log_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get full detail of a single LLM call log."""
    log = await session.get(LLMLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="LLM log not found")
    return log
