"""Observability helpers: structured logging and Prometheus metrics setup.

This module provides a simple initializer for production-style structured logs
and basic Prometheus metric registration. Import and call `init_observability()`
from application startup.
"""
from __future__ import annotations

import logging
from typing import Optional

try:
    from prometheus_client import Counter, Histogram, start_http_server
except Exception:  # pragma: no cover - optional dependency fallback
    Counter = None
    Histogram = None
    start_http_server = None


class _NoopMetric:
    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs) -> None:
        return None

    def observe(self, *args, **kwargs) -> None:
        return None


REQUEST_COUNTER = (
    Counter("app_requests_total", "Total application requests", ["endpoint", "method", "status"])
    if Counter is not None
    else _NoopMetric()
)
REQUEST_LATENCY = (
    Histogram("app_request_latency_seconds", "Request latency seconds", ["endpoint"])
    if Histogram is not None
    else _NoopMetric()
)


def init_observability(prometheus_port: Optional[int] = None) -> None:
    """Initialize logging and start Prometheus HTTP server (optional).

    Args:
        prometheus_port: if provided, starts an HTTP server exposing metrics.
    """
    # Structured JSON-like logging via basicConfig; in production swap for structlog or logging.config
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s'
    )

    if prometheus_port and start_http_server is not None:
        try:
            start_http_server(prometheus_port)
            logging.getLogger(__name__).info("Prometheus metrics server started on port %d", prometheus_port)
        except Exception:
            logging.getLogger(__name__).exception("Failed to start Prometheus server")
    elif prometheus_port:
        logging.getLogger(__name__).warning("prometheus_client is not installed; skipping metrics server startup")
