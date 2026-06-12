"""Integration tests for the full scraper → extraction → DB pipeline.

Run with:
    pytest tests/integration/test_pipeline.py -v
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_scheme_extractor_with_html():
    """SchemeExtractor should parse a minimal HTML snippet without crashing."""
    from app.scraping.extractors.scheme_extractor import SchemeExtractor

    extractor = SchemeExtractor()
    html = """
    <html><body>
    <h1>PM-KISAN Samman Nidhi</h1>
    <p>Farmers with income below Rs 2,00,000 per year are eligible.</p>
    <p>Age: 18-65 years. Documents: Aadhaar, Bank Account.</p>
    </body></html>
    """
    result = extractor._extract_with_fallback(html, source_url="https://pmkisan.gov.in")
    assert result is not None
    assert result.record.name != ""
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_knowledge_graph_seed_and_search():
    """KnowledgeGraphOrchestrator should ingest fixtures and return results."""
    from app.agents.dependencies import DEFAULT_SCHEME_FIXTURES
    from app.graph.knowledge_graph import KnowledgeGraphOrchestrator

    orchestrator = KnowledgeGraphOrchestrator()
    await orchestrator.initialize()

    for scheme in DEFAULT_SCHEME_FIXTURES[:2]:
        ok = await orchestrator.ingest_scheme(scheme)
        assert ok is True

    results = await orchestrator.hybrid_search(
        query="agricultural financial assistance for farmers",
        user_profile={"state": "Central", "occupation": "farmer"},
        top_k=3,
    )
    assert len(results) > 0


@pytest.mark.asyncio
async def test_eligibility_engine_evaluates_profile():
    """EligibilityEngine should return a result for a farmer profile."""
    from app.eligibility.engine import EligibilityEngine

    engine = EligibilityEngine()
    profile = {
        "age": 35,
        "income": 100000,
        "occupation": "farmer",
        "state": "Tamil Nadu",
        "land_hectares": 2.5,
    }
    rules = {
        "and": [
            {">=": [{"var": "age"}, 18]},
            {"<=": [{"var": "income"}, 200000]},
            {"in": [{"var": "occupation"}, ["farmer"]]},
        ]
    }
    result = engine.evaluate(profile, rules)
    assert result is not None
    assert result.eligible is True
    assert result.score > 0


@pytest.mark.asyncio
async def test_rag_retriever_graph_query_fallback():
    """graph_query should gracefully return hits from in-memory graph when Neo4j is absent."""
    from app.agents.dependencies import DEFAULT_SCHEME_FIXTURES
    from app.graph.knowledge_graph import KnowledgeGraphOrchestrator

    # Seed the module-level singleton manually
    import app.agents.dependencies as deps
    orchestrator = KnowledgeGraphOrchestrator()
    await orchestrator.initialize()
    for scheme in DEFAULT_SCHEME_FIXTURES:
        await orchestrator.ingest_scheme(scheme)
    deps._graph_orchestrator = orchestrator

    from unittest.mock import MagicMock
    from app.rag.retriever import HybridRetriever

    retriever = HybridRetriever(
        vector_store=MagicMock(),
        embedder=MagicMock(),
        reranker=MagicMock(),
    )
    hits = await retriever.graph_query(
        query="farmer scheme Tamil Nadu",
        user_profile={"state": "Tamil Nadu", "occupation": "farmer"},
    )
    # Should return in-memory graph hits because Neo4j is not running in test
    assert isinstance(hits, list)


@pytest.mark.asyncio
async def test_graph_ingestor_builds_cypher():
    """GraphIngestor._build_cypher_statements should produce non-empty statements."""
    from app.graph.ingestion import GraphIngestor

    ingestor = GraphIngestor()
    scheme = {
        "scheme_id": "TEST-001",
        "name": "Test Scheme",
        "state": "Central",
        "ministry": "Ministry of Test",
        "target_beneficiaries": ["farmers", "women"],
        "documents_required": [{"type": "identity", "name": "Aadhaar"}],
        "eligibility": {"caste_category": ["SC", "ST"]},
    }
    stmts = ingestor._build_cypher_statements(scheme)
    assert len(stmts) > 0
    # Should contain MERGE statements
    assert any("MERGE" in s for s in stmts)
    # Should reference the scheme_id
    assert any("TEST-001" in s for s in stmts)
