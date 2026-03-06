"""Knowledge management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.enterprise import EnterpriseContext, log_audit_event, require_role
from app.enterprise.resources import require_workspace_resource
from app.knowledge import knowledge_generator, knowledge_graph, knowledge_retriever
from app.models import DataSource
from app.models.membership import WorkspaceRole
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
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    from app.execution import sql_executor

    datasource = await require_workspace_resource(
        session,
        DataSource,
        data.datasource_id,
        context.workspace.id,
        "DataSource not found",
    )

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
        workspace_id=context.workspace.id,
    )
    await knowledge_graph.populate_from_knowledge(
        session,
        knowledge,
        data.datasource_id,
        workspace_id=context.workspace.id,
    )
    await log_audit_event(
        session,
        context,
        action="knowledge.generate",
        resource_type="datasource",
        resource_id=datasource.id,
        details={"tables": len(tables), "scripts": len(data.scripts)},
    )

    return {"status": "success", "knowledge": knowledge}


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    query: str,
    datasource_id: str | None = None,
    top_k: int = 10,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.VIEWER)),
    session: AsyncSession = Depends(get_session),
):
    results = await knowledge_retriever.retrieve(
        session,
        query,
        datasource_id=datasource_id,
        top_k=top_k,
        workspace_id=context.workspace.id,
    )

    nodes = []
    scores = []
    for node, score in results:
        nodes.append(
            KnowledgeNodeResponse(
                id=node.id,
                workspace_id=node.workspace_id,
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
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.VIEWER)),
    session: AsyncSession = Depends(get_session),
):
    await require_workspace_resource(
        session,
        DataSource,
        datasource_id,
        context.workspace.id,
        "DataSource not found",
    )
    nodes = await knowledge_graph.get_nodes_by_datasource(
        session,
        datasource_id,
        workspace_id=context.workspace.id,
    )
    tree = await knowledge_graph.get_tree(session, workspace_id=context.workspace.id)
    return {"nodes_count": len(nodes), "tree": tree}


@router.post("/knowledge/nodes", response_model=KnowledgeNodeResponse, status_code=201)
async def create_knowledge_node(
    data: KnowledgeNodeCreate,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    if data.datasource_id:
        await require_workspace_resource(
            session,
            DataSource,
            data.datasource_id,
            context.workspace.id,
            "DataSource not found",
        )
    node = await knowledge_graph.add_node(
        session,
        node_type=data.node_type,
        name=data.name,
        parent_id=data.parent_id,
        components=data.components,
        datasource_id=data.datasource_id,
        workspace_id=context.workspace.id,
    )
    await session.flush()
    await log_audit_event(
        session,
        context,
        action="knowledge.node.create",
        resource_type="knowledge_node",
        resource_id=node.id,
        details={"name": node.name, "node_type": node.node_type.value},
    )
    return node
