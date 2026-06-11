from __future__ import annotations

import asyncio
import time
import logging
from typing import Optional, Any
from app.agents.state import AgentState

try:
    from app.core.observability import REQUEST_COUNTER, REQUEST_LATENCY
except Exception:
    REQUEST_COUNTER: Optional[Any] = None
    REQUEST_LATENCY: Optional[Any] = None

logger = logging.getLogger(__name__)


class RetrievalAgent:
    def __init__(self, hybrid_retriever=None, timeout_seconds: int = 10, max_retries: int = 2):
        self.retriever = hybrid_retriever
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def retrieve(self, state: AgentState) -> dict:
        query = (state.get("query") or "").strip()
        profile = state.get("user_profile", {}) or {}

        if not query:
            return {"retrieved_chunks": []}

        start = time.time()
        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            attempt += 1
            try:
                if self.retriever:
                    # Use asyncio timeout to avoid hanging retrievals
                    hits = await asyncio.wait_for(
                        self.retriever.retrieve(query, user_profile=profile),
                        timeout=self.timeout_seconds,
                    )
                    chunks = [
                        {"content": getattr(h, "content", ""), "score": float(getattr(h, "score", 0.0)), "metadata": getattr(h, "metadata", {})}
                        for h in hits
                    ]
                else:
                    chunks = [
                        {"content": "Mock retrieved content for query: " + query, "score": 0.0, "metadata": {"source": "mock"}}
                    ]

                latency = round(time.time() - start, 3)
                if REQUEST_COUNTER:
                    try:
                        REQUEST_COUNTER.labels(endpoint="retrieval", method="retrieve", status="ok").inc()
                    except Exception:
                        pass
                if REQUEST_LATENCY:
                    try:
                        REQUEST_LATENCY.labels(endpoint="retrieval").observe(latency)
                    except Exception:
                        pass

                return {"retrieved_chunks": chunks, "latency_s": latency}

            except asyncio.TimeoutError as te:
                last_error = te
                logger.warning("Retrieval timeout (attempt %d/%d) for query: %s", attempt, self.max_retries, query)
                # try again until max_retries
                continue
            except Exception as exc:
                last_error = exc
                logger.exception("Error during retrieval (attempt %d/%d): %s", attempt, self.max_retries, exc)
                break

        # If we reach here, retrieval failed
        err_msg = str(last_error) if last_error else "retrieval_failed"
        if REQUEST_COUNTER:
            try:
                REQUEST_COUNTER.labels(endpoint="retrieval", method="retrieve", status="error").inc()
            except Exception:
                pass

        return {"retrieved_chunks": [], "error_code": "retrieval_failed", "error_message": err_msg}
