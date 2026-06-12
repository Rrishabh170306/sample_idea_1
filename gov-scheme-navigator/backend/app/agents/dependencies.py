from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

from app.core.config import Settings
from app.graph.knowledge_graph import KnowledgeGraphOrchestrator
from app.profile_identity import profile_key_from_user_id
from app.profile_store import FileProfileStore

logger = logging.getLogger(__name__)

# Module-level singleton — populated lazily via _async_seed_graph() called from lifespan
_graph_orchestrator: KnowledgeGraphOrchestrator | None = None

DEFAULT_SCHEME_FIXTURES: list[dict[str, Any]] = [
    {
        "scheme_id": "PM-KISAN-001",
        "name": "PM-KISAN Samman Nidhi",
        "state": "Central",
        "category": ["agriculture", "direct_benefit"],
        "target_beneficiaries": ["farmers", "small_farmers"],
        "benefits": {"type": "cash_transfer", "amount": 6000, "frequency": "annual",
                     "description": "Annual income support of Rs 6000 in 3 instalments"},
        "documents_required": [{"type": "identity", "name": "Aadhaar"},
                                {"type": "land", "name": "Land records"}],
        "eligibility": {
            "caste_category": ["General", "OBC", "SC", "ST"],
            "occupation": ["farmer"],
            "age_min": 18,
        },
        "department": "Department of Agriculture and Farmers Welfare",
        "ministry": "Ministry of Agriculture and Farmers Welfare",
        "official_url": "https://pmkisan.gov.in",
    },
    {
        "scheme_id": "KCC-001",
        "name": "Kisan Credit Card",
        "state": "Central",
        "category": ["agriculture", "credit"],
        "target_beneficiaries": ["farmers"],
        "benefits": {"type": "credit", "amount": 300000, "frequency": "revolving",
                     "description": "Short-term credit up to Rs 3 lakh at 7% interest"},
        "documents_required": [{"type": "identity", "name": "Aadhaar"},
                                {"type": "financial", "name": "Bank passbook"}],
        "eligibility": {
            "caste_category": ["General", "OBC", "SC", "ST"],
            "occupation": ["farmer"],
        },
        "department": "Department of Financial Services",
        "ministry": "Ministry of Finance",
        "official_url": "https://www.india.gov.in/spotlight/kisan-credit-card",
    },
    {
        "scheme_id": "PMFBY-001",
        "name": "Pradhan Mantri Fasal Bima Yojana",
        "state": "Central",
        "category": ["agriculture", "insurance"],
        "target_beneficiaries": ["farmers"],
        "benefits": {"type": "insurance", "amount": None, "frequency": "seasonal",
                     "description": "Crop insurance against natural calamities, pests and diseases"},
        "documents_required": [{"type": "identity", "name": "Aadhaar"},
                                {"type": "land", "name": "Sowing certificate"}],
        "eligibility": {
            "caste_category": ["General", "OBC", "SC", "ST"],
            "occupation": ["farmer"],
            "land_ownership_required": True,
        },
        "department": "Department of Agriculture",
        "ministry": "Ministry of Agriculture and Farmers Welfare",
        "official_url": "https://pmfby.gov.in",
    },
    {
        "scheme_id": "TN-FARMERS-RELIEF-001",
        "name": "Tamil Nadu Farmers Relief Fund",
        "state": "Tamil Nadu",
        "category": ["agriculture", "relief"],
        "target_beneficiaries": ["farmers"],
        "benefits": {"type": "cash_transfer", "amount": 2000, "frequency": "one_time",
                     "description": "One-time relief payment for Tamil Nadu farmers"},
        "documents_required": [{"type": "identity", "name": "Aadhaar"},
                                {"type": "land", "name": "Patta (land ownership document)"}],
        "eligibility": {
            "states": ["Tamil Nadu"],
            "occupation": ["farmer"],
            "land_hectares_max": 5.0,
        },
        "department": "Agriculture Department",
        "ministry": "Government of Tamil Nadu",
        "official_url": "https://www.tn.gov.in/agriculture",
    },
]


async def _async_seed_graph() -> None:
    """Initialise and seed the module-level KnowledgeGraphOrchestrator.

    Called from main.py lifespan — safe to await directly.
    """
    global _graph_orchestrator
    try:
        orchestrator = KnowledgeGraphOrchestrator()
        await orchestrator.initialize()
        for scheme in DEFAULT_SCHEME_FIXTURES:
            await orchestrator.ingest_scheme(scheme)
        _graph_orchestrator = orchestrator
        logger.info("KnowledgeGraphOrchestrator seeded with %d fixture schemes",
                    len(DEFAULT_SCHEME_FIXTURES))
    except Exception:
        logger.exception("Failed to seed KnowledgeGraphOrchestrator")
        _graph_orchestrator = None


def get_graph_orchestrator() -> KnowledgeGraphOrchestrator | None:
    """Return the module-level graph orchestrator (set during startup)."""
    return _graph_orchestrator


def create_graph_orchestrator() -> KnowledgeGraphOrchestrator:
    """Synchronous factory to create and seed an isolated graph orchestrator instance.
    
    Used primarily for tests. Does not touch the global _graph_orchestrator.
    """
    import asyncio
    orchestrator = KnowledgeGraphOrchestrator()
    
    async def _init_and_seed():
        await orchestrator.initialize()
        for scheme in DEFAULT_SCHEME_FIXTURES:
            await orchestrator.ingest_scheme(scheme)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import threading
        def _run_in_thread():
            asyncio.run(_init_and_seed())
        t = threading.Thread(target=_run_in_thread)
        t.start()
        t.join()
    else:
        asyncio.run(_init_and_seed())

    return orchestrator


class FileProfileCRUDAdapter:
    def __init__(self, store: FileProfileStore) -> None:
        self.store = store

    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        return (
            self.store.get_profile(profile_key_from_user_id(user_id))
            or self.store.get_profile(user_id)
        )

    def create_or_update_profile(
        self, user_id: str, profile_data: dict[str, Any]
    ) -> dict[str, Any]:
        profile_key = profile_key_from_user_id(user_id)
        existing = (
            self.store.get_profile(profile_key)
            or self.store.get_profile(user_id)
            or {}
        )
        return self.store.upsert_profile(profile_key, {**existing, **profile_data})


class GraphBackedRetrieverAdapter:
    def __init__(self, graph_orchestrator: KnowledgeGraphOrchestrator) -> None:
        self.graph_orchestrator = graph_orchestrator

    async def retrieve(
        self, query: str, user_profile: dict[str, Any] | None = None
    ) -> list[SimpleNamespace]:
        results = await self.graph_orchestrator.hybrid_search(
            query, user_profile or {}, top_k=5
        )
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
                    metadata={"id": scheme_id, "source": source, "scheme_name": name},
                )
            )
        return hits


def create_profile_crud(settings: Settings) -> FileProfileCRUDAdapter:
    return FileProfileCRUDAdapter(FileProfileStore(settings.profile_store_path))


def create_retriever(settings: Settings, graph_orchestrator: KnowledgeGraphOrchestrator | None):
    """Build the best available retriever.

    Priority:
    1. RAG HybridRetriever (if DATABASE_URL is set and pgvector is available)
    2. GraphBackedRetrieverAdapter (in-memory graph)
    3. None (orchestrator will handle gracefully)
    """
    if settings.database_url:
        try:
            from app.db.vector_store import VectorStore
            from app.rag.embedder import EmbeddingService
            from app.rag.reranker import CrossEncoderReranker
            from app.rag.retriever import HybridRetriever

            vector_store = VectorStore(settings.database_url)
            embedder = EmbeddingService()
            reranker = CrossEncoderReranker()
            logger.info("Using HybridRetriever (pgvector + sentence-transformers)")
            return HybridRetriever(vector_store, embedder, reranker)
        except Exception:
            logger.exception(
                "Failed to initialise HybridRetriever — falling back to graph retrieval"
            )

    if graph_orchestrator is not None:
        logger.info("Using GraphBackedRetrieverAdapter (in-memory graph)")
        return GraphBackedRetrieverAdapter(graph_orchestrator)

    logger.warning("No retriever available — agent will have empty retrieval results")
    return None
