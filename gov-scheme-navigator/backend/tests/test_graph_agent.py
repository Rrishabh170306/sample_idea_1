import asyncio

from app.agents.dependencies import create_graph_orchestrator
from app.agents.graph_agent import GraphAgent


def test_graph_agent_uses_seeded_knowledge_graph_service() -> None:
    graph_orchestrator = create_graph_orchestrator()
    assert graph_orchestrator is not None

    result = asyncio.run(
        GraphAgent(graph_orchestrator=graph_orchestrator).query(
            {
                "query": "What schemes are available for farmers?",
                "user_profile": {
                    "state": "Central",
                    "occupation": "farmers",
                },
            }
        )
    )

    graph_results = result["graph_results"]
    assert graph_results
    assert all(item["name"] != "Mock Graph Node" for item in graph_results)
    assert all(item["scheme_id"] != "MOCK_REL" for item in graph_results)
    assert graph_results[0]["scheme_id"]
    assert graph_results[0]["name"]
    assert graph_results[0]["source"]


def test_graph_agent_reports_missing_graph_dependency() -> None:
    result = asyncio.run(
        GraphAgent(graph_orchestrator=None).query(
            {
                "query": "What schemes are available for farmers?",
                "user_profile": {
                    "state": "Central",
                    "occupation": "farmers",
                },
            }
        )
    )

    assert result["graph_results"] == []
    assert result["error_code"] == "graph_not_configured"
