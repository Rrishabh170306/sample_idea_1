from __future__ import annotations
from app.agents.state import AgentState

class QueryClassifier:
    def __init__(self, llm_client=None):
        self.llm = llm_client

    def classify(self, state: AgentState) -> dict:
        query = state.get("query", "")
        query_lower = query.lower()
        
        # Mocking LLM classification logic with keywords
        if any(word in query_lower for word in ["eligible", "am i", "can i get", "qualify"]):
            q_type = "eligibility"
        elif any(word in query_lower for word in ["compare", "vs", "better"]):
            q_type = "comparison"
        elif any(word in query_lower for word in ["apply", "how to", "needed"]):
            q_type = "application"
        elif any(word in query_lower for word in ["verify", "certificate", "upload", "document"]):
            q_type = "document"
        elif any(word in query_lower for word in ["why", "explain"]):
            q_type = "reasoning"
        else:
            q_type = "general"
            
        return {"query_type": q_type}
