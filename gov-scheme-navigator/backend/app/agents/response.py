from __future__ import annotations

from typing import Any
from app.agents.state import AgentState

def compose_response(answer: str, citations: list[dict[str, Any]]) -> str:
    citation_block = "\n".join(f"- {citation['source_url']}" for citation in citations)
    if citation_block:
        return f"{answer}\n\nSources:\n{citation_block}"
    return answer

class ResponseAgent:
    def generate(self, state: AgentState) -> dict:
        q_type = state.get("query_type", "general")
        citations = state.get("citations", [])
        eligibility = state.get("eligibility_results", {})
        
        if q_type == "eligibility" and eligibility:
            answer = f"Based on your profile, here are your eligibility results: {eligibility}"
        elif q_type == "document":
            answer = "We have processed and verified your documents."
        else:
            answer = "Here is the information we found based on your query."
            
        final_response = compose_response(answer, citations)
        return {"response": final_response}
