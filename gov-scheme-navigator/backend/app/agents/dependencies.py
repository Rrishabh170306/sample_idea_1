from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Any

from app.core.config import Settings
from app.graph.knowledge_graph import KnowledgeGraphOrchestrator
from app.profile_identity import profile_key_from_user_id
from app.profile_store import FileProfileStore

logger = logging.getLogger(__name__)


DEFAULT_SCHEME_FIXTURES: list[dict[str, Any]] = [
    {
        "scheme_id": "PM-KISAN-001",
        "name": "PM-KISAN Samman Nidhi",
        "state": "Central",
        "category": ["agriculture", "direct_benefit"],
        "target_beneficiaries": ["farmers", "small_farmers"],
        "benefits": {"type": "cash_transfer", "amount": 6000},
        "documents_required": [{"type": "identity", "name": "Aadhaar"}],
        "eligibility": {"caste_category": ["General", "OBC", "SC", "ST"]},
        "department": "Department of Agriculture",
        "ministry": "Ministry of Agriculture",
    },
    {
        "scheme_id": "KCC-001",
        "name": "Kisan Credit Card",
        "state": "Central",
        "category": ["agriculture", "credit"],
        "target_beneficiaries": ["farmers"],
        "benefits": {"type": "credit", "amount": 300000},
        "documents_required": [{"type": "financial", "name": "Bank Account"}],
        "eligibility": {"caste_category": ["General", "OBC", "SC", "ST"]},
        "department": "Department of Agriculture",
        "ministry": "Ministry of Agriculture",
    },
]


class FileProfileCRUDAdapter:
    def __init__(self, store: FileProfileStore) -> None:
        self.store = store

    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        return self.store.get_profile(profile_key_from_user_id(user_id)) or self.store.get_profile(user_id)

    def create_or_update_profile(self, user_id: str, profile_data: dict[str, Any]) -> dict[str, Any]:
        profile_key = profile_key_from_user_id(user_id)
        existing = self.store.get_profile(profile_key) or self.store.get_profile(user_id) or {}
        return self.store.upsert_profile(profile_key, {**existing, **profile_data})


class GraphBackedRetrieverAdapter:
    def __init__(self, graph_orchestrator: KnowledgeGraphOrchestrator) -> None:
        self.graph_orchestrator = graph_orchestrator

    async def retrieve(self, query: str, user_profile: dict[str, Any] | None = None) -> list[SimpleNamespace]:
        results = await self.graph_orchestrator.hybrid_search(query, user_profile or {}, top_k=5)
        hits: list[SimpleNamespace] = []

        for result in results:
            name = getattr(result, "name", "") or "Unknown scheme"
            scheme_id = getattr(result, "scheme_id", "") or ""
            source = getattr(result, "source", "graph")
            score = float(getattr(result, "relevance_score", 0.0))
            hits.append(
                SimpleNamespace(
                    content=f"Scheme: {name}",
                    score=score,
                    metadata={
                        "id": scheme_id,
                        "source": source,
                        "scheme_name": name,
                    },
                )
            )

        return hits


async def _build_seeded_graph_orchestrator() -> KnowledgeGraphOrchestrator:
    graph_orchestrator = KnowledgeGraphOrchestrator()
    await graph_orchestrator.initialize()

    for scheme in DEFAULT_SCHEME_FIXTURES:
        await graph_orchestrator.ingest_scheme(scheme)

    return graph_orchestrator


def create_graph_orchestrator() -> KnowledgeGraphOrchestrator | None:
    try:
        return asyncio.run(_build_seeded_graph_orchestrator())
    except Exception as exc:
        logger.exception("Failed to initialize seeded graph orchestrator: %s", exc)
        return None


def create_profile_crud(settings: Settings) -> FileProfileCRUDAdapter:
    return FileProfileCRUDAdapter(FileProfileStore(settings.profile_store_path))


def create_retriever(settings: Settings, graph_orchestrator: KnowledgeGraphOrchestrator | None):
    if settings.database_url:
        try:
            from app.db.vector_store import VectorStore
            from app.rag.embedder import EmbeddingService
            from app.rag.reranker import CrossEncoderReranker
            from app.rag.retriever import HybridRetriever

            vector_store = VectorStore(settings.database_url)
            embedder = EmbeddingService()
            reranker = CrossEncoderReranker()
            return HybridRetriever(vector_store, embedder, reranker)
        except Exception as exc:
            logger.exception("Failed to initialize RAG retriever, falling back to graph-backed retrieval: %s", exc)

    if graph_orchestrator is not None:
        return GraphBackedRetrieverAdapter(graph_orchestrator)

    return None
