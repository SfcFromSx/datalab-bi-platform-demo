"""Data source management API endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.execution import sql_executor
from app.models import DataSource, DataSourceType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["datasources"])


class DataSourceCreate(BaseModel):
    name: str
    ds_type: DataSourceType = DataSourceType.DUCKDB
    connection_string: str = ""


class DataSourceResponse(BaseModel):
    id: str
    name: str
    ds_type: str
    metadata: dict | None = None

    model_config = {"from_attributes": True}


class SQLQueryRequest(BaseModel):
    query: str


@router.get("/datasources", response_model=list[DataSourceResponse])
async def list_datasources(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(DataSource))
    datasources = result.scalars().all()
    return [
        DataSourceResponse(
            id=ds.id, name=ds.name, ds_type=ds.ds_type.value, metadata=ds.metadata_
        )
        for ds in datasources
    ]


@router.post("/datasources", response_model=DataSourceResponse, status_code=201)
async def create_datasource(
    data: DataSourceCreate,
    session: AsyncSession = Depends(get_session),
):
    ds = DataSource(
        name=data.name,
        ds_type=data.ds_type,
        connection_string=data.connection_string,
    )
    session.add(ds)
    await session.flush()
    await session.refresh(ds)
    return DataSourceResponse(
        id=ds.id, name=ds.name, ds_type=ds.ds_type.value, metadata=ds.metadata_
    )


@router.post("/datasources/upload-csv", response_model=DataSourceResponse)
async def upload_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    table_name = Path(file.filename).stem.replace(" ", "_").replace("-", "_")

    data_dir = Path("./data/uploads")
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / file.filename

    content = await file.read()
    file_path.write_bytes(content)

    try:
        sql_executor.register_csv(table_name, str(file_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load CSV: {e}")

    schema = sql_executor.get_schema(table_name)
    row_count_result = sql_executor.execute(f'SELECT COUNT(*) FROM "{table_name}"')

    ds = DataSource(
        name=table_name,
        ds_type=DataSourceType.CSV,
        connection_string=str(file_path),
        metadata_={
            "schema": schema,
            "row_count": row_count_result.get("rows", [[0]])[0][0],
            "file_path": str(file_path),
        },
    )
    session.add(ds)
    await session.flush()
    await session.refresh(ds)

    return DataSourceResponse(
        id=ds.id, name=ds.name, ds_type=ds.ds_type.value, metadata=ds.metadata_
    )


@router.get("/datasources/{datasource_id}/schema")
async def get_datasource_schema(
    datasource_id: str,
    session: AsyncSession = Depends(get_session),
):
    ds = await session.get(DataSource, datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail="DataSource not found")

    tables = sql_executor.get_tables(datasource_id)
    result = {}
    for table in tables:
        result[table] = sql_executor.get_schema(table, datasource_id)

    if not result and ds.metadata_ and "schema" in ds.metadata_:
        table_name = ds.name
        result[table_name] = ds.metadata_["schema"]

    return {"datasource_id": datasource_id, "tables": result}


@router.post("/datasources/{datasource_id}/query")
async def query_datasource(
    datasource_id: str,
    data: SQLQueryRequest,
    session: AsyncSession = Depends(get_session),
):
    ds = await session.get(DataSource, datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail="DataSource not found")

    result = sql_executor.execute(data.query, datasource_id)
    return result
