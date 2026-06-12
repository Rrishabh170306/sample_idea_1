from __future__ import annotations

import asyncio
import logging

from langgraph.graph import StateGraph, START, END

from app.agents.dependencies import get_graph_orchestrator, create_profile_crud, create_retriever
from app.agents.state import AgentState
from app.agents.classifier import QueryClassifier
from app.agents.profile import ProfileAgent
from app.agents.eligibility_agent import EligibilityAgent
from app.agents.retrieval import RetrievalAgent
from app.agents.graph_agent import GraphAgent
from app.agents.document import DocumentAgent
from app.agents.verification import VerificationAgent
from app.agents.citation import CitationAgent
from app.agents.response import ResponseAgent
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        settings = get_settings()
        graph_orchestrator = get_graph_orchestrator()
        profile_crud = create_profile_crud(settings)
        retriever = create_retriever(settings, graph_orchestrator)

        self.classifier = QueryClassifier()
        self.profile = ProfileAgent(profile_crud=profile_crud)
        self.eligibility = EligibilityAgent()
        self.retrieval = RetrievalAgent(hybrid_retriever=retriever)
        self.graph = GraphAgent(graph_orchestrator=graph_orchestrator)
        self.document = DocumentAgent()
        self.verification = VerificationAgent()
        self.citation = CitationAgent()
        self.response = ResponseAgent()

    def build_graph(self):
        builder = StateGraph(AgentState)
        
        # Add Nodes
        builder.add_node("classifier", self.classifier.classify)
        builder.add_node("profile", self.profile.load_profile)
        builder.add_node("eligibility", self.eligibility.evaluate)
        builder.add_node("retrieval", self.retrieval.retrieve)
        builder.add_node("graph", self.graph.query)
        builder.add_node("document", self.document.process)
        builder.add_node("verification", self.verification.verify)
        builder.add_node("citation", self.citation.attach)
        builder.add_node("response_agent", self.response.generate)
        
        # Add Edges
        builder.add_edge(START, "classifier")
        
        # Conditional Edge after classifier
        def route_query(state: AgentState):
            q_type = state.get("query_type", "general")
            if q_type == "eligibility":
                return "profile"
            elif q_type == "document":
                return "document"
            else:  # comparison, application, general, reasoning
                return "profile"
                
        builder.add_conditional_edges("classifier", route_query, {
            "profile": "profile",
            "document": "document",
        })
        
        # Profile-driven routing
        def route_profile(state: AgentState):
            if state.get("query_type") == "eligibility":
                return "eligibility"
            return "retrieval"

        builder.add_conditional_edges("profile", route_profile, {
            "eligibility": "eligibility",
            "retrieval": "retrieval",
        })

        # Eligibility flow
        builder.add_edge("eligibility", "graph")

        # Retrieval flow
        builder.add_edge("retrieval", "graph")
        
        # Document flow
        builder.add_edge("document", "profile")
        
        # Common end flow
        builder.add_edge("graph", "verification")
        
        # Conditional Edge after verification
        def route_verification(state: AgentState):
            if state.get("needs_human_review", False):
                logger.warning("Human review needed, routing to citation directly for now.")
                return "citation"
            return "citation"
            
        builder.add_conditional_edges("verification", route_verification, {
            "citation": "citation"
        })
        
        builder.add_edge("citation", "response_agent")
        builder.add_edge("response_agent", END)
        
        return builder.compile()

    async def arun(self, state: AgentState) -> AgentState:
        graph = self.build_graph()
        return await graph.ainvoke(state)

    def run(self, state: AgentState) -> AgentState:
        return asyncio.run(self.arun(state))
