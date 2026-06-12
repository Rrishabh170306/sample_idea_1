"""
Point 3: Knowledge Graph (Neo4j) System
Handles graph schema, relationships, GraphRAG queries, and hybrid search.
"""

from __future__ import annotations

import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import uuid4


logger = logging.getLogger(__name__)
from app.core.config import settings
# Expose optional components at module level so tests can patch them.
try:
    from app.rag.embedder import EmbeddingService
except Exception:
    EmbeddingService = None

try:
    from app.db.vector_store import VectorStore
except Exception:
    VectorStore = None


# ============================================================================
# 1. GRAPH SCHEMA DEFINITIONS
# ============================================================================


class NodeType(str, Enum):
    """Neo4j node types."""
    SCHEME = "Scheme"
    STATE = "State"
    DEPARTMENT = "Department"
    MINISTRY = "Ministry"
    BENEFICIARY_TYPE = "BeneficiaryType"
    DOCUMENT = "Document"
    ELIGIBILITY_RULE = "EligibilityRule"
    CATEGORY = "Category"


class RelationType(str, Enum):
    """Neo4j relationship types."""
    HAS_SCHEME = "HAS_SCHEME"
    OVERSEES = "OVERSEES"
    MANAGES = "MANAGES"
    ELIGIBLE_FOR = "ELIGIBLE_FOR"
    REQUIRES_DOCUMENT = "REQUIRES_DOCUMENT"
    HAS_ELIGIBILITY = "HAS_ELIGIBILITY"
    TARGETS_CATEGORY = "TARGETS_CATEGORY"
    SIMILAR_TO = "SIMILAR_TO"
    SUPERSEDES = "SUPERSEDES"


@dataclass
class GraphNode:
    """Represents a Neo4j node."""
    id: str
    node_type: NodeType
    properties: dict[str, Any]
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()

    def to_cypher_properties(self) -> str:
        """Convert properties to a Cypher map literal.

        Uses Python `repr` for safe string quoting and handles basic types.
        """
        props = dict(self.properties or {})
        props["id"] = self.id
        props["created_at"] = self.created_at.isoformat()
        props["updated_at"] = self.updated_at.isoformat()

        def _format_value(v: Any) -> str:
            if v is None:
                return "null"
            if isinstance(v, str):
                return repr(v)
            if isinstance(v, bool):
                return "true" if v else "false"
            if isinstance(v, (int, float)):
                return str(v)
            if isinstance(v, dict):
                inner = ", ".join(f"{k}: {_format_value(val)}" for k, val in v.items())
                return f"{{{inner}}}"
            if isinstance(v, (list, tuple)):
                inner = ", ".join(_format_value(x) for x in v)
                return f"[{inner}]"
            return repr(str(v))

        formatted = ", ".join(f"{k}: {_format_value(v)}" for k, v in props.items())
        return f"{{{formatted}}}"


@dataclass
class GraphRelationship:
    """Represents a Neo4j relationship."""
    source_id: str
    target_id: str
    rel_type: RelationType
    properties: dict[str, Any] = None
    created_at: datetime = None

    def __post_init__(self):
        if not self.properties:
            self.properties = {}
        if not self.created_at:
            self.created_at = datetime.utcnow()


class SchemeNode(GraphNode):
    """Scheme node in graph."""
    def __init__(self, scheme_id: str, name: str, **properties):
        super().__init__(
            id=scheme_id,
            node_type=NodeType.SCHEME,
            properties={
                "name": name,
                "status": properties.get("status", "active"),
                "category": properties.get("category", []),
                "benefit_type": properties.get("benefit_type"),
                "benefit_amount": properties.get("benefit_amount"),
                **{k: v for k, v in properties.items()
                   if k not in ["status", "category", "benefit_type", "benefit_amount"]}
            }
        )


class StateNode(GraphNode):
    """State node in graph."""
    def __init__(self, state_code: str, state_name: str):
        super().__init__(
            id=state_code,
            node_type=NodeType.STATE,
            properties={"name": state_name, "code": state_code}
        )


class DepartmentNode(GraphNode):
    """Department node in graph."""
    def __init__(self, dept_name: str):
        super().__init__(
            id=dept_name.lower().replace(" ", "_"),
            node_type=NodeType.DEPARTMENT,
            properties={"name": dept_name}
        )


class MinistryNode(GraphNode):
    """Ministry node in graph."""
    def __init__(self, ministry_name: str):
        super().__init__(
            id=ministry_name.lower().replace(" ", "_"),
            node_type=NodeType.MINISTRY,
            properties={"name": ministry_name}
        )


class BeneficiaryTypeNode(GraphNode):
    """Beneficiary type node (farmer, student, woman, etc.)."""
    def __init__(self, beneficiary_type: str):
        super().__init__(
            id=beneficiary_type.lower(),
            node_type=NodeType.BENEFICIARY_TYPE,
            properties={"type": beneficiary_type}
        )


class DocumentNode(GraphNode):
    """Required document node."""
    def __init__(self, doc_type: str, doc_name: str):
        super().__init__(
            id=f"{doc_type}_{doc_name}".lower().replace(" ", "_"),
            node_type=NodeType.DOCUMENT,
            properties={"type": doc_type, "name": doc_name}
        )


class CategoryNode(GraphNode):
    """Category node (SC, ST, OBC, General)."""
    def __init__(self, category_name: str):
        super().__init__(
            id=category_name.lower(),
            node_type=NodeType.CATEGORY,
            properties={"name": category_name}
        )


class EligibilityRuleNode(GraphNode):
    """Eligibility rule node (age > 18, income < 500000, etc.)."""
    def __init__(self, field: str, operator: str, value: Any):
        rule_id = f"rule_{field}_{operator}_{str(value)}".lower().replace(" ", "_")
        super().__init__(
            id=rule_id,
            node_type=NodeType.ELIGIBILITY_RULE,
            properties={
                "field": field,
                "operator": operator,
                "value": str(value)
            }
        )


# ============================================================================
# 2. RELATIONSHIP MANAGEMENT
# ============================================================================


class GraphBuilder:
    """
    Build and manage graph relationships.
    Handles node creation and relationship setup.
    """

    def __init__(self):
        self.nodes: dict[str, GraphNode] = {}
        self.relationships: list[GraphRelationship] = []
        self.stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "errors": 0,
        }

    def add_node(self, node: GraphNode) -> bool:
        """Add node to graph."""
        try:
            if node.id in self.nodes:
                logger.debug(f"Node {node.id} already exists. Updating...")
                self.nodes[node.id] = node
            else:
                self.nodes[node.id] = node
                self.stats["nodes_created"] += 1

            logger.debug(f"Added node: {node.id} ({node.node_type})")
            return True
        except Exception as e:
            logger.error(f"Error adding node {node.id}: {e}")
            self.stats["errors"] += 1
            return False

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationType,
        properties: dict = None,
    ) -> bool:
        """Add relationship between nodes."""
        try:
            if source_id not in self.nodes:
                logger.warning(f"Source node {source_id} not found. Creating placeholder...")
                self.nodes[source_id] = GraphNode(source_id, NodeType.SCHEME, {})

            if target_id not in self.nodes:
                logger.warning(f"Target node {target_id} not found. Creating placeholder...")
                self.nodes[target_id] = GraphNode(target_id, NodeType.SCHEME, {})

            rel = GraphRelationship(source_id, target_id, rel_type, properties)
            self.relationships.append(rel)
            self.stats["relationships_created"] += 1

            logger.debug(f"Added relationship: {source_id} -[{rel_type}]-> {target_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding relationship: {e}")
            self.stats["errors"] += 1
            return False

    def build_from_scheme(self, scheme_data: dict) -> bool:
        """
        Build graph structure from scheme data.
        Creates scheme node and related nodes + relationships.
        """
        try:
            scheme_id = scheme_data.get("scheme_id", f"scheme_{uuid4()}")

            # Create main scheme node
            scheme_node = SchemeNode(
                scheme_id=scheme_id,
                name=scheme_data.get("name", "Unknown"),
                status=scheme_data.get("status", "active"),
                category=scheme_data.get("category", []),
                benefit_type=scheme_data.get("benefits", {}).get("type"),
                benefit_amount=scheme_data.get("benefits", {}).get("amount"),
            )
            self.add_node(scheme_node)

            # Create state node and relationship
            state = scheme_data.get("state", "Central")
            state_node = StateNode(state.upper(), state)
            self.add_node(state_node)
            self.add_relationship(state_node.id, scheme_node.id, RelationType.HAS_SCHEME)

            # Create ministry/department nodes
            ministry = scheme_data.get("ministry")
            if ministry:
                ministry_node = MinistryNode(ministry)
                self.add_node(ministry_node)
                self.add_relationship(
                    ministry_node.id, scheme_node.id, RelationType.MANAGES
                )

            department = scheme_data.get("department")
            if department:
                dept_node = DepartmentNode(department)
                self.add_node(dept_node)
                self.add_relationship(
                    dept_node.id, scheme_node.id, RelationType.MANAGES
                )

                if ministry:
                    self.add_relationship(
                        ministry_node.id, dept_node.id, RelationType.OVERSEES
                    )

            # Create beneficiary type nodes
            for beneficiary in scheme_data.get("target_beneficiaries", []):
                ben_node = BeneficiaryTypeNode(beneficiary)
                self.add_node(ben_node)
                self.add_relationship(
                    ben_node.id, scheme_node.id, RelationType.ELIGIBLE_FOR
                )

            # Create document nodes
            for doc in scheme_data.get("documents_required", []):
                doc_type = doc.get("type", "general") if isinstance(doc, dict) else "general"
                doc_name = doc.get("name", "") if isinstance(doc, dict) else str(doc)
                
                if doc_name:
                    doc_node = DocumentNode(doc_type, doc_name)
                    self.add_node(doc_node)
                    self.add_relationship(
                        scheme_node.id, doc_node.id, RelationType.REQUIRES_DOCUMENT
                    )

            # Create category nodes (SC, ST, OBC)
            caste_category = (
                scheme_data.get("eligibility", {}).get("caste_category")
            )
            if caste_category:
                for category in caste_category:
                    cat_node = CategoryNode(category)
                    self.add_node(cat_node)
                    self.add_relationship(
                        scheme_node.id, cat_node.id, RelationType.TARGETS_CATEGORY
                    )

            logger.info(f"Built graph for scheme: {scheme_id}")
            return True

        except Exception as e:
            logger.error(f"Error building graph from scheme: {e}")
            self.stats["errors"] += 1
            return False

    def export_to_cypher(self) -> str:
        """Export graph as Cypher queries."""
        queries = []

        # Create nodes
        for node in self.nodes.values():
            # Use node_type value as label
            label = node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type)
            query = f"CREATE (n:{label} {node.to_cypher_properties()})"
            queries.append(query)

        # Create relationships
        for rel in self.relationships:
            # Match by id property and create relationship with properties
            rel_type = rel.rel_type.value if hasattr(rel.rel_type, 'value') else str(rel.rel_type)
            props = ""
            if rel.properties:
                # Safely format relationship properties using repr for values
                props_map = ", ".join(f"{k}: {repr(v)}" for k, v in (rel.properties or {}).items())
                props = f" {{{props_map}}}"

            query = (
                f"MATCH (a {{id: {repr(rel.source_id)}}}) "
                f"MATCH (b {{id: {repr(rel.target_id)}}}) "
                f"CREATE (a)-[:{rel_type}{props}]->(b)"
            )
            queries.append(query)

        return "\n".join(queries)

    def get_stats(self) -> dict:
        """Get graph building statistics."""
        return {
            **self.stats,
            "total_nodes": len(self.nodes),
            "total_relationships": len(self.relationships),
        }


# ============================================================================
# 3. GRAPHRAG QUERY ENGINE
# ============================================================================


class GraphQuery:
    """Query interface for graph traversal."""

    def __init__(self, graph_builder: GraphBuilder):
        self.builder = graph_builder

    @staticmethod
    def _scheme_payload(node: GraphNode) -> dict:
        return {"id": node.id, **(node.properties or {})}

    def find_schemes_by_state(self, state: str) -> list[dict]:
        """Find all schemes in a state."""
        results = []

        for node in self.builder.nodes.values():
            if node.node_type == NodeType.STATE and node.properties.get("name") == state:
                # Find schemes related to this state
                for rel in self.builder.relationships:
                    if rel.rel_type == RelationType.HAS_SCHEME and rel.source_id == node.id:
                        scheme_node = self.builder.nodes.get(rel.target_id)
                        if scheme_node:
                            results.append(self._scheme_payload(scheme_node))

        return results

    def find_schemes_by_beneficiary(self, beneficiary_type: str) -> list[dict]:
        """Find schemes for a specific beneficiary type."""
        results = []

        for node in self.builder.nodes.values():
            if node.node_type == NodeType.BENEFICIARY_TYPE:
                node_type_val = (node.properties.get("type") or "").lower()
                target = (beneficiary_type or "").lower()

                # Normalize simple plural/singular differences and substring matches
                def _norm(x: str) -> str:
                    return x.rstrip("s") if x.endswith("s") else x

                if _norm(node_type_val) == _norm(target) or target in node_type_val or node_type_val in target:
                    # Find schemes eligible for this beneficiary
                    for rel in self.builder.relationships:
                        if (rel.rel_type == RelationType.ELIGIBLE_FOR and
                            rel.source_id == node.id):
                            scheme_node = self.builder.nodes.get(rel.target_id)
                            if scheme_node:
                                results.append(self._scheme_payload(scheme_node))

        return results

    def find_schemes_by_category(self, category: str) -> list[dict]:
        """Find schemes targeting a specific category (SC, ST, OBC)."""
        results = []

        for node in self.builder.nodes.values():
            if (node.node_type == NodeType.CATEGORY and
                node.properties.get("name").lower() == category.lower()):
                # Find schemes targeting this category
                for rel in self.builder.relationships:
                    if (rel.rel_type == RelationType.TARGETS_CATEGORY and
                        rel.target_id == node.id):
                        scheme_node = self.builder.nodes.get(rel.source_id)
                        if scheme_node:
                            results.append(self._scheme_payload(scheme_node))

        return results

    def find_schemes_for_profile(
        self, state: str, beneficiary_type: str, category: Optional[str] = None
    ) -> list[dict]:
        """
        Multi-hop query: Find schemes for specific user profile.
        Example: "Schemes for SC farmers in UP"
        """
        schemes_by_state = set(s["id"] for s in self.find_schemes_by_state(state))
        schemes_by_beneficiary = set(
            s["id"] for s in self.find_schemes_by_beneficiary(beneficiary_type)
        )

        # Intersection of results
        results = list(schemes_by_state & schemes_by_beneficiary)

        # Filter by category if provided
        if category:
            schemes_by_category = set(
                s["id"] for s in self.find_schemes_by_category(category)
            )
            results = list(set(results) & schemes_by_category)

        # Return full scheme data
        return [self._scheme_payload(self.builder.nodes[scheme_id]) for scheme_id in results]

    def count_schemes_by_ministry(self) -> dict[str, int]:
        """Aggregation query: Count schemes per ministry."""
        ministry_counts = {}

        for rel in self.builder.relationships:
            if rel.rel_type == RelationType.MANAGES:
                ministry_node = self.builder.nodes.get(rel.source_id)
                if ministry_node and ministry_node.node_type == NodeType.MINISTRY:
                    ministry_name = ministry_node.properties.get("name")
                    ministry_counts[ministry_name] = ministry_counts.get(ministry_name, 0) + 1

        return ministry_counts

    def count_schemes_by_beneficiary(self) -> dict[str, int]:
        """Count schemes per beneficiary type."""
        beneficiary_counts = {}

        for rel in self.builder.relationships:
            if rel.rel_type == RelationType.ELIGIBLE_FOR:
                ben_node = self.builder.nodes.get(rel.source_id)
                if ben_node and ben_node.node_type == NodeType.BENEFICIARY_TYPE:
                    ben_type = ben_node.properties.get("type")
                    beneficiary_counts[ben_type] = beneficiary_counts.get(ben_type, 0) + 1

        return beneficiary_counts


# ============================================================================
# 4. HYBRID SEARCH INTEGRATION (Vector + Graph + BM25)
# ============================================================================


@dataclass
class SearchResult:
    """Individual search result."""
    scheme_id: str
    name: str
    relevance_score: float
    source: str  # "vector", "graph", "bm25"
    metadata: dict = None


class HybridRetriever:
    """
    Combine vector search, graph traversal, and BM25 full-text search.
    Uses Reciprocal Rank Fusion (RRF) for result merging.
    """

    def __init__(self, graph_builder: GraphBuilder, embedding_model=None):
        self.graph = GraphQuery(graph_builder)
        self.embedding_model = embedding_model
        self.builder = graph_builder

    async def hybrid_retrieve(
        self,
        query: str,
        user_profile: dict,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Hybrid retrieval: combine multiple search methods.

        Args:
            query: User query string
            user_profile: {"state": str, "category": str, "occupation": str}
            top_k: Number of results to return

        Returns:
            List of ranked SearchResult objects
        """
        # 1. Vector search for semantic similarity
        vector_results = await self._vector_search(query)

        # 2. Graph traversal for structured matching
        graph_results = self._graph_search(user_profile)

        # 3. BM25 full-text search
        bm25_results = self._bm25_search(query)

        # 4. RRF fusion
        fused_results = self._reciprocal_rank_fusion(
            vector_results, graph_results, bm25_results, k=60
        )

        # 5. Cross-encoder reranking (optional)
        reranked = self._cross_encoder_rerank(query, fused_results[:top_k * 2])

        return reranked[:top_k]

    async def _vector_search(self, query: str) -> list[SearchResult]:
        """Vector similarity search."""
        results = []

        try:
            # Use module-level VectorStore, EmbeddingService, settings, and asyncio
            if not getattr(settings, "database_url", None):
                logger.warning("Database URL not set. Skipping real vector search.")
                return results

            embedder = self.embedding_model or EmbeddingService()

            dsn = settings.database_url
            if "postgresql" in dsn and "asyncpg" not in dsn:
                dsn = dsn.replace("postgresql://", "postgresql+asyncpg://").replace("postgresql+psycopg2://", "postgresql+asyncpg://")

            vector_store = VectorStore(dsn)

            if hasattr(embedder, "embed_query"):
                embedding = await asyncio.to_thread(embedder.embed_query, query)
            elif hasattr(embedder, "embed_texts"):
                # fallback if only embed_texts is implemented
                embedding = await asyncio.to_thread(lambda: embedder.embed_texts([query])[0])
            else:
                logger.warning("Embedder has no known method to embed query")
                return results

            vector_hits = await vector_store.vector_search(embedding, top_k=5)

            for hit in vector_hits:
                scheme_id = hit.get("scheme_id")
                name = hit.get("metadata", {}).get("name", "Unknown Scheme")
                
                # Try to get the name from the in-memory graph if not in metadata
                if name == "Unknown Scheme" and scheme_id in self.builder.nodes:
                    name = self.builder.nodes[scheme_id].properties.get("name", "Unknown Scheme")

                results.append(
                    SearchResult(
                        scheme_id=scheme_id,
                        name=name,
                        relevance_score=hit.get("score", 0.0),
                        source="vector",
                        metadata=hit.get("metadata", {})
                    )
                )

        except Exception as e:
            logger.warning(f"Vector search failed (fallback to empty list): {e}")

        return results

    def _graph_search(self, user_profile: dict) -> list[SearchResult]:
        """Graph-based structured search."""
        results = []

        try:
            schemes = self.graph.find_schemes_for_profile(
                state=user_profile.get("state", "Central"),
                beneficiary_type=user_profile.get("occupation", ""),
                category=user_profile.get("category"),
            )

            for scheme_data in schemes:
                results.append(
                    SearchResult(
                        scheme_id=scheme_data.get("id", ""),
                        name=scheme_data.get("name", ""),
                        relevance_score=0.9,  # High confidence from structured matching
                        source="graph",
                        metadata={
                            "benefit_type": scheme_data.get("benefit_type"),
                            "benefit_amount": scheme_data.get("benefit_amount"),
                            "category": scheme_data.get("category", []),
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Graph search error: {e}")

        return results

    def _bm25_search(self, query: str) -> list[SearchResult]:
        """Full-text BM25 search."""
        results = []

        try:
            # Simple keyword matching (mock BM25)
            query_terms = set(query.lower().split())

            for node in self.builder.nodes.values():
                if node.node_type == NodeType.SCHEME:
                    scheme_name = node.properties.get("name", "").lower()
                    matches = len(query_terms & set(scheme_name.split()))

                    if matches > 0:
                        score = matches / len(query_terms)
                        results.append(
                            SearchResult(
                                scheme_id=node.id,
                                name=node.properties.get("name", ""),
                                relevance_score=score,
                                source="bm25",
                                metadata={
                                    "benefit_type": node.properties.get("benefit_type"),
                                    "benefit_amount": node.properties.get("benefit_amount"),
                                    "category": node.properties.get("category", []),
                                },
                            )
                        )

        except Exception as e:
            logger.error(f"BM25 search error: {e}")

        return results

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[SearchResult],
        graph_results: list[SearchResult],
        bm25_results: list[SearchResult],
        k: int = 60,
    ) -> list[SearchResult]:
        """
        Reciprocal Rank Fusion algorithm.
        Combines multiple ranked lists without score normalization.
        RRF(d) = sum(1 / (k + rank(d)))
        """
        rrf_scores = {}

        # Process each ranking
        for results in [vector_results, graph_results, bm25_results]:
            for rank, result in enumerate(results, start=1):
                if result.scheme_id not in rrf_scores:
                    rrf_scores[result.scheme_id] = {"results": result, "score": 0}

                rrf_scores[result.scheme_id]["score"] += 1 / (k + rank)

        # Sort by RRF score
        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        return [SearchResult(
            scheme_id=r["results"].scheme_id,
            name=r["results"].name,
            relevance_score=r["score"],
            source="hybrid_rrf",
            metadata={
                **(r["results"].metadata or {}),
                "component_scores": {"vector": 0.3, "graph": 0.5, "bm25": 0.2},
            }
        ) for r in sorted_results]

    def _cross_encoder_rerank(
        self, query: str, candidates: list[SearchResult]
    ) -> list[SearchResult]:
        """Re-rank results using cross-encoder for better relevance."""
        # Mock reranking - in production, use cross-encoder model
        return sorted(candidates, key=lambda x: x.relevance_score, reverse=True)


# ============================================================================
# 5. GRAPH MAINTENANCE
# ============================================================================


class GraphMaintenance:
    """Maintain graph integrity: versioning, cleanup, index management."""

    def __init__(self, graph_builder: GraphBuilder):
        self.builder = graph_builder
        self.version = "1.0"
        self.last_updated = datetime.utcnow()

    def add_version_tracking(self, scheme_id: str, old_scheme_data: dict, new_scheme_data: dict):
        """Track scheme version changes with SUPERSEDES relationship."""
        try:
            old_version_id = f"{scheme_id}_v{self.version}"
            new_version_id = f"{scheme_id}_v{float(self.version) + 0.1}"

            # Create relationship
            self.builder.add_relationship(
                new_version_id,
                old_version_id,
                RelationType.SUPERSEDES,
                {"changed_fields": self._get_changed_fields(old_scheme_data, new_scheme_data)},
            )

            logger.info(f"Version tracking added: {old_version_id} -> {new_version_id}")

        except Exception as e:
            logger.error(f"Error adding version tracking: {e}")

    def add_similarity_relationships(self, scheme_id: str, similar_schemes: list[str]):
        """Add SIMILAR_TO relationships between schemes."""
        try:
            for similar_scheme_id in similar_schemes:
                self.builder.add_relationship(
                    scheme_id,
                    similar_scheme_id,
                    RelationType.SIMILAR_TO,
                    {"similarity_score": 0.85},
                )

            logger.info(f"Added {len(similar_schemes)} similarity relationships for {scheme_id}")

        except Exception as e:
            logger.error(f"Error adding similarity relationships: {e}")

    def cleanup_deprecated_nodes(self) -> int:
        """Remove deprecated nodes and relationships."""
        removed_count = 0

        try:
            # Remove nodes with status='inactive' (mock)
            nodes_to_remove = [
                node_id for node_id, node in self.builder.nodes.items()
                if node.properties.get("status") == "inactive"
            ]

            for node_id in nodes_to_remove:
                del self.builder.nodes[node_id]
                removed_count += 1

            logger.info(f"Removed {removed_count} deprecated nodes")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        return removed_count

    def rebuild_indexes(self) -> bool:
        """Rebuild graph indexes for performance."""
        try:
            # Mock index rebuild
            logger.info(f"Rebuilding indexes. Total nodes: {len(self.builder.nodes)}")
            self.last_updated = datetime.utcnow()
            return True
        except Exception as e:
            logger.error(f"Error rebuilding indexes: {e}")
            return False

    def get_health_status(self) -> dict:
        """Get graph health statistics."""
        return {
            "version": self.version,
            "total_nodes": len(self.builder.nodes),
            "total_relationships": len(self.builder.relationships),
            "last_updated": self.last_updated.isoformat(),
            "nodes_by_type": self._count_nodes_by_type(),
            "relationships_by_type": self._count_relationships_by_type(),
        }

    def _count_nodes_by_type(self) -> dict:
        """Count nodes by type."""
        counts = {}
        for node in self.builder.nodes.values():
            node_type = str(node.node_type)
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts

    def _count_relationships_by_type(self) -> dict:
        """Count relationships by type."""
        counts = {}
        for rel in self.builder.relationships:
            rel_type = str(rel.rel_type)
            counts[rel_type] = counts.get(rel_type, 0) + 1
        return counts

    @staticmethod
    def _get_changed_fields(old_data: dict, new_data: dict) -> list[str]:
        """Identify changed fields between versions."""
        changed = []
        for key in set(list(old_data.keys()) + list(new_data.keys())):
            if old_data.get(key) != new_data.get(key):
                changed.append(key)
        return changed


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================


class KnowledgeGraphOrchestrator:
    """Main orchestrator for knowledge graph operations."""

    def __init__(self):
        self.builder = GraphBuilder()
        self.query_engine = None
        self.hybrid_retriever = None
        self.maintenance = GraphMaintenance(self.builder)

    async def initialize(self):
        """Initialize graph engine."""
        self.query_engine = GraphQuery(self.builder)
        self.hybrid_retriever = HybridRetriever(self.builder)
        logger.info("Knowledge Graph Orchestrator initialized")

    async def ingest_scheme(self, scheme_data: dict) -> bool:
        """Ingest a scheme into the knowledge graph."""
        try:
            self.builder.build_from_scheme(scheme_data)
            logger.info(f"Ingested scheme: {scheme_data.get('scheme_id')}")
            return True
        except Exception as e:
            logger.error(f"Error ingesting scheme: {e}")
            return False

    async def query(self, query_type: str, params: dict) -> Any:
        """Execute graph query."""
        try:
            if query_type == "schemes_by_state":
                return self.query_engine.find_schemes_by_state(params.get("state"))

            elif query_type == "schemes_by_beneficiary":
                return self.query_engine.find_schemes_by_beneficiary(
                    params.get("beneficiary_type")
                )

            elif query_type == "schemes_for_profile":
                return self.query_engine.find_schemes_for_profile(
                    state=params.get("state"),
                    beneficiary_type=params.get("beneficiary_type"),
                    category=params.get("category"),
                )

            elif query_type == "count_by_ministry":
                return self.query_engine.count_schemes_by_ministry()

            elif query_type == "count_by_beneficiary":
                return self.query_engine.count_schemes_by_beneficiary()

            else:
                logger.warning(f"Unknown query type: {query_type}")
                return None

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return None

    async def hybrid_search(
        self, query: str, user_profile: dict, top_k: int = 5
    ) -> list[SearchResult]:
        """Execute hybrid search."""
        try:
            results = await self.hybrid_retriever.hybrid_retrieve(
                query, user_profile, top_k
            )
            return results
        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            return []

    def get_graph_stats(self) -> dict:
        """Get comprehensive graph statistics."""
        return {
            "builder_stats": self.builder.get_stats(),
            "health_status": self.maintenance.get_health_status(),
        }
