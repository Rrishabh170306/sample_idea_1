from __future__ import annotations

from typing import Sequence


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
    def verify(self, response: str) -> dict[str, object]:
        raise NotImplementedError("Verification pipeline will be implemented here.")
