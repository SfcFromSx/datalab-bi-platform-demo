"""Knowledge management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.knowledge import knowledge_generator, knowledge_graph, knowledge_retriever
from app.models import DataSource
from app.schemas import (
    KnowledgeGenerateRequest,
    KnowledgeNodeCreate,
    KnowledgeNodeResponse,
    KnowledgeSearchResponse,
)

router = APIRouter(tags=["knowledge"])


@router.post("/knowledge/generate")
async def generate_knowledge(
    data: KnowledgeGenerateRequest,
    session: AsyncSession = Depends(get_session),
):
    from app.execution import sql_executor

    datasource = await session.get(DataSource, data.datasource_id)
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")

    tables = sql_executor.get_tables(data.datasource_id)
    schema_parts = []
    for table in tables:
        cols = sql_executor.get_schema(table, data.datasource_id)
        col_strs = [f"  {c['column_name']} ({c['column_type']})" for c in cols]
        schema_parts.append(f"Table: {table}\n" + "\n".join(col_strs))
    schema = "\n\n".join(schema_parts)

    knowledge = await knowledge_generator.generate(
        schema=schema,
        scripts=data.scripts,
    )

    await knowledge_graph.delete_for_datasource(
        session,
        data.datasource_id,
        workspace_id="local",
    )
    await knowledge_graph.populate_from_knowledge(
        session,
        knowledge,
        data.datasource_id,
        workspace_id="local",
    )

    return {"status": "success", "knowledge": knowledge}


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    query: str,
    datasource_id: str | None = None,
    top_k: int = 10,
    session: AsyncSession = Depends(get_session),
):
    results = await knowledge_retriever.retrieve(
        session,
        query,
        datasource_id=datasource_id,
        top_k=top_k,
        workspace_id="local",
    )

    nodes = []
    scores = []
    for node, score in results:
        nodes.append(
            KnowledgeNodeResponse(
                id=node.id,
                node_type=node.node_type.value,
                name=node.name,
                parent_id=node.parent_id,
                components=node.components,
                datasource_id=node.datasource_id,
                created_at=node.created_at,
                updated_at=node.updated_at,
            )
        )
        scores.append(score)

    return KnowledgeSearchResponse(nodes=nodes, scores=scores)


@router.get("/knowledge/graph/{datasource_id}")
async def get_knowledge_graph(
    datasource_id: str,
    session: AsyncSession = Depends(get_session),
):
    ds = await session.get(DataSource, datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail="DataSource not found")

    nodes = await knowledge_graph.get_nodes_by_datasource(
        session,
        datasource_id,
        workspace_id="local",
    )
    tree = await knowledge_graph.get_tree(session, workspace_id="local")
    return {"nodes_count": len(nodes), "tree": tree}


@router.post("/knowledge/nodes", response_model=KnowledgeNodeResponse, status_code=201)
async def create_knowledge_node(
    data: KnowledgeNodeCreate,
    session: AsyncSession = Depends(get_session),
):
    if data.datasource_id:
        ds = await session.get(DataSource, data.datasource_id)
        if not ds:
            raise HTTPException(status_code=404, detail="DataSource not found")

    node = await knowledge_graph.add_node(
        session,
        node_type=data.node_type,
        name=data.name,
        parent_id=data.parent_id,
        components=data.components,
        datasource_id=data.datasource_id,
        workspace_id="local",
    )
    await session.flush()
    return node
