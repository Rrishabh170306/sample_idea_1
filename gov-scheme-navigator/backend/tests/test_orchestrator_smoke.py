from app.agents.orchestrator import Orchestrator


def test_orchestrator_runs_minimal_query() -> None:
    state = {"query": "What schemes are available for farmers?"}

    result = Orchestrator().run(state)

    assert result["query"] == state["query"]
    assert result["response"]
    assert isinstance(result["response"], str)
