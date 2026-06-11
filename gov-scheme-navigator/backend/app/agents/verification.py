from __future__ import annotations

from typing import Sequence
from app.agents.state import AgentState

def compute_confidence(scores: Sequence[float], weights: Sequence[float] | None = None) -> float:
    if not scores:
        return 0.0
    if weights is None:
        weights = [1.0 / len(scores)] * len(scores)
    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0
    normalized = [weight / total_weight for weight in weights]
    return sum(score * weight for score, weight in zip(scores, normalized, strict=False))

class VerificationAgent:
    def verify(self, state: AgentState) -> dict:
        chunks = state.get("retrieved_chunks", [])
        citations = state.get("citations", [])
        eligibility = state.get("eligibility_results", {})
        
        # 1. Retrieval Relevance
        retrieval_relevance = 0.0
        if chunks:
            retrieval_relevance = sum(c.get("score", 0.0) for c in chunks) / len(chunks)
        
        # 2. Citation Coverage
        # Simulated logic: if we cited stuff and we had chunks
        citation_coverage = 1.0 if citations else (0.0 if chunks else 1.0)
        
        # 3. Rule Agreement
        # If eligibility engine evaluated successfully
        rule_agreement = 1.0 if eligibility else 0.5
        
        # 4. Source Freshness (Simulated 1.0)
        source_freshness = 1.0
        
        scores_dict = {
            "retrieval_relevance": retrieval_relevance,
            "citation_coverage": citation_coverage,
            "rule_agreement": rule_agreement,
            "source_freshness": source_freshness
        }
        
        weights_dict = {
            "retrieval_relevance": 0.3,
            "citation_coverage": 0.3,
            "rule_agreement": 0.25,
            "source_freshness": 0.15
        }
        
        score_list = list(scores_dict.values())
        weight_list = list(weights_dict.values())
        
        final_confidence = compute_confidence(score_list, weight_list)
            
        needs_review = final_confidence < 0.8
        return {"confidence_score": final_confidence, "needs_human_review": needs_review}
