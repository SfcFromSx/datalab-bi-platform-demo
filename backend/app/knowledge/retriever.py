"""Knowledge Retriever - Coarse-to-fine retrieval from the knowledge graph.

Implements Algorithm 2 from the DataLab paper:
- Coarse-Grained Retrieval: Lexical + Semantic search
- Fine-Grained Ordering: Weighted scoring (lexical + semantic + LLM)
- Top-K Selection
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.graph import knowledge_graph
from app.llm.client import LLMClient, llm_client
from app.models.knowledge import KnowledgeNode, KnowledgeNodeType

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """Coarse-to-fine knowledge retrieval from the knowledge graph."""

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        weights: tuple[float, float, float] = (0.3, 0.3, 0.4),
    ):
        self.llm = llm or llm_client
        self.w_lex, self.w_sem, self.w_llm = weights

    async def retrieve(
        self,
        session: AsyncSession,
        query: str,
        datasource_id: Optional[str] = None,
        top_k: int = 10,
        workspace_id: Optional[str] = None,
    ) -> list[tuple[KnowledgeNode, float]]:
        coarse_nodes = await self._coarse_retrieval(
            session,
            query,
            datasource_id,
        )

        if not coarse_nodes:
            return []

        primary_nodes = []
        for node in coarse_nodes:
            if node.node_type == KnowledgeNodeType.ALIAS and node.parent_id:
                parent = await knowledge_graph.get_node(
                    session,
                    node.parent_id,
                )
                if parent:
                    primary_nodes.append(parent)
            else:
                primary_nodes.append(node)

        seen_ids = set()
        unique_nodes = []
        for node in primary_nodes:
            if node.id not in seen_ids:
                seen_ids.add(node.id)
                unique_nodes.append(node)

        scored_nodes = await self._fine_grained_ordering(query, unique_nodes)
        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        return scored_nodes[:top_k]

    async def _coarse_retrieval(
        self,
        session: AsyncSession,
        query: str,
        datasource_id: Optional[str] = None,
    ) -> list[KnowledgeNode]:
        """Lexical + semantic search for initial candidate set."""
        lexical_results = await knowledge_graph.search_by_name(
            session,
            query,
            limit=50,
        )

        if datasource_id:
            ds_nodes = await knowledge_graph.get_nodes_by_datasource(
                session,
                datasource_id,
            )
            name_matches = [
                n for n in ds_nodes
                if any(
                    term.lower() in n.name.lower()
                    for term in query.lower().split()
                )
            ]
            combined = list(lexical_results) + name_matches
        else:
            combined = list(lexical_results)

        seen = set()
        unique = []
        for node in combined:
            if node.id not in seen:
                seen.add(node.id)
                unique.append(node)

        return unique

    async def _fine_grained_ordering(
        self, query: str, nodes: list[KnowledgeNode]
    ) -> list[tuple[KnowledgeNode, float]]:
        """Score each node with lexical + semantic + LLM relevance."""
        scored = []
        for node in nodes:
            lex_score = self._lexical_score(query, node)
            sem_score = self._semantic_score(query, node)
            llm_score = await self._llm_score(query, node) if len(nodes) <= 20 else 0.5

            total = self.w_lex * lex_score + self.w_sem * sem_score + self.w_llm * llm_score
            scored.append((node, total))

        return scored

    def _lexical_score(self, query: str, node: KnowledgeNode) -> float:
        """Token-based matching score."""
        query_tokens = set(query.lower().split())
        node_tokens = set(node.name.lower().split())
        if node.components:
            desc = node.components.get("description", "")
            if desc:
                node_tokens.update(desc.lower().split())

        if not query_tokens:
            return 0.0

        overlap = query_tokens & node_tokens
        return len(overlap) / len(query_tokens)

    def _semantic_score(self, query: str, node: KnowledgeNode) -> float:
        """Simple character-level similarity as a lightweight fallback."""
        node_text = node.name
        if node.components and node.components.get("description"):
            node_text += " " + node.components["description"]

        query_chars = set(query.lower())
        node_chars = set(node_text.lower())
        if not query_chars:
            return 0.0

        return len(query_chars & node_chars) / len(query_chars | node_chars)

    async def _llm_score(self, query: str, node: KnowledgeNode) -> float:
        """LLM-based relevance scoring."""

        node_info = f"Name: {node.name}, Type: {node.node_type.value}"
        if node.components:
            node_info += f", Description: {node.components.get('description', 'N/A')}"

        prompt = """Rate the relevance of this knowledge node to the query on a scale of 0.0 to 1.0.

Query: {query}
Node: {node_info}

Respond with ONLY a JSON object: {{"score": <0.0-1.0>}}""".format(
            query=query,
            node_info=node_info,
        )

        try:
            result = await self.llm.complete_json(
                [{"role": "user", "content": prompt}]
            )
            return float(result.get("score", 0.5))
        except Exception:
            return 0.5


knowledge_retriever = KnowledgeRetriever()
