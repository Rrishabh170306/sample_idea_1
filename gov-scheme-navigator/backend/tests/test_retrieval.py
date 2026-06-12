import asyncio

from app.agents.dependencies import GraphBackedRetrieverAdapter, create_graph_orchestrator, create_retriever
from app.agents.retrieval import RetrievalAgent
from app.core.config import get_settings
from app.rag.chunker import chunk_text


def test_chunk_text_splits_text() -> None:
    chunks = chunk_text("one two three four five six", chunk_size=3, overlap=1)

    assert len(chunks) >= 2
    assert chunks[0].content.startswith("one two three")


def test_retrieval_agent_uses_graph_backed_repository_adapter(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    graph_orchestrator = create_graph_orchestrator()
    retriever = create_retriever(settings, graph_orchestrator)

    assert isinstance(retriever, GraphBackedRetrieverAdapter)

    result = asyncio.run(
        RetrievalAgent(hybrid_retriever=retriever).retrieve(
            {
                "query": "What schemes are available for farmers?",
                "user_profile": {
                    "state": "Central",
                    "occupation": "farmers",
                },
            }
        )
    )

    chunks = result["retrieved_chunks"]
    assert chunks
    assert all("Mock retrieved content" not in chunk["content"] for chunk in chunks)
    assert chunks[0]["content"].startswith("Scheme: ")
    assert chunks[0]["metadata"]["id"]
    assert chunks[0]["metadata"]["scheme_name"]

    get_settings.cache_clear()
