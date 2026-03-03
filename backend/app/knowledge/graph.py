"""Knowledge Graph - Tree-based structure for organizing domain knowledge.

Structure: Database → Table → Column → Value, with Alias nodes
for synonyms and acronyms.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeNode, KnowledgeNodeType

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Manages the tree-based knowledge graph for domain knowledge organization."""

    async def add_node(
        self,
        session: AsyncSession,
        node_type: KnowledgeNodeType,
        name: str,
        parent_id: Optional[str] = None,
        components: Optional[dict] = None,
        datasource_id: Optional[str] = None,
    ) -> KnowledgeNode:
        node = KnowledgeNode(
            node_type=node_type,
            name=name,
            parent_id=parent_id,
            components=components or {},
            datasource_id=datasource_id,
        )
        session.add(node)
        await session.flush()
        return node

    async def get_node(self, session: AsyncSession, node_id: str) -> Optional[KnowledgeNode]:
        result = await session.execute(select(KnowledgeNode).where(KnowledgeNode.id == node_id))
        return result.scalar_one_or_none()

    async def get_tree(
        self, session: AsyncSession, root_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Get the knowledge tree starting from a root node."""
        if root_id:
            stmt = select(KnowledgeNode).where(KnowledgeNode.parent_id == root_id)
        else:
            stmt = select(KnowledgeNode).where(KnowledgeNode.parent_id.is_(None))

        result = await session.execute(stmt)
        nodes = result.scalars().all()

        tree = []
        for node in nodes:
            node_dict = {
                "id": node.id,
                "type": node.node_type.value,
                "name": node.name,
                "components": node.components,
                "children": await self.get_tree(session, node.id),
            }
            tree.append(node_dict)
        return tree

    async def get_nodes_by_datasource(
        self, session: AsyncSession, datasource_id: str
    ) -> list[KnowledgeNode]:
        result = await session.execute(
            select(KnowledgeNode).where(KnowledgeNode.datasource_id == datasource_id)
        )
        return list(result.scalars().all())

    async def search_by_name(
        self, session: AsyncSession, query: str, limit: int = 20
    ) -> list[KnowledgeNode]:
        """Lexical search: find nodes whose name contains the query."""
        result = await session.execute(
            select(KnowledgeNode)
            .where(KnowledgeNode.name.ilike(f"%{query}%"))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def populate_from_knowledge(
        self,
        session: AsyncSession,
        knowledge: dict[str, Any],
        datasource_id: str,
    ) -> None:
        """Populate the knowledge graph from generated knowledge components."""
        db_info = knowledge.get("database", {})
        db_node = await self.add_node(
            session,
            KnowledgeNodeType.DATABASE,
            db_info.get("name", "database"),
            components=db_info,
            datasource_id=datasource_id,
        )

        table_info = knowledge.get("table", {})
        table_node = await self.add_node(
            session,
            KnowledgeNodeType.TABLE,
            table_info.get("name", "table"),
            parent_id=db_node.id,
            components=table_info,
            datasource_id=datasource_id,
        )

        columns = knowledge.get("columns", {})
        for col_name, col_info in columns.items():
            await self.add_node(
                session,
                KnowledgeNodeType.COLUMN,
                col_name,
                parent_id=table_node.id,
                components=col_info,
                datasource_id=datasource_id,
            )

    async def delete_for_datasource(
        self, session: AsyncSession, datasource_id: str
    ) -> int:
        nodes = await self.get_nodes_by_datasource(session, datasource_id)
        count = len(nodes)
        for node in nodes:
            await session.delete(node)
        return count


knowledge_graph = KnowledgeGraph()
