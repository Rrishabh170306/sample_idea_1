import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.graph.knowledge_graph import HybridRetriever, GraphBuilder, SearchResult


@pytest.mark.asyncio
async def test_vector_search_real_implementation():
    """Verify that _vector_search properly calls VectorStore and maps results."""
    # Mock settings and injected services
    builder = GraphBuilder()
    retriever = HybridRetriever(builder)
    
    with patch("app.graph.knowledge_graph.settings") as mock_settings, \
         patch("app.graph.knowledge_graph.EmbeddingService") as MockEmbeddingService, \
         patch("app.graph.knowledge_graph.VectorStore") as MockVectorStore, \
         patch("app.graph.knowledge_graph.asyncio.to_thread") as mock_to_thread:
        
        # Configure mocked settings
        mock_settings.database_url = "postgresql+asyncpg://user:pass@localhost/db"
        
        # Configure mock VectorStore
        mock_vs_instance = MagicMock()
        # vector_search returns list of dictionaries
        mock_vs_instance.vector_search = AsyncMock(return_value=[
            {
                "scheme_id": "SCHEME-001",
                "metadata": {"name": "Test Scheme 1"},
                "score": 0.95
            },
            {
                "scheme_id": "SCHEME-002",
                "metadata": {"name": "Test Scheme 2"},
                "score": 0.85
            }
        ])
        MockVectorStore.return_value = mock_vs_instance
        
        # Configure mock EmbeddingService / to_thread
        mock_to_thread.return_value = [0.1, 0.2, 0.3]
        
        # Execute
        results = await retriever._vector_search("test query")
        
        # Verify
        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert results[0].scheme_id == "SCHEME-001"
        assert results[0].name == "Test Scheme 1"
        assert results[0].relevance_score == 0.95
        assert results[0].source == "vector"

        assert results[1].scheme_id == "SCHEME-002"
        assert results[1].name == "Test Scheme 2"
        assert results[1].relevance_score == 0.85

        mock_vs_instance.vector_search.assert_called_once_with([0.1, 0.2, 0.3], top_k=5)
