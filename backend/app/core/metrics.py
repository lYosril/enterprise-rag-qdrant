"""
Prometheus metrics for the core RAG pipeline.

Uses _get_or_create to survive pytest re-imports without raising
DuplicateTimeseries errors.
"""

from typing import Any

from prometheus_client import REGISTRY, Counter, Histogram


def _get_or_create(metric_cls, name: str, documentation: str, **kwargs) -> Any:
    """Return an existing registered metric or create a new one."""
    existing = REGISTRY._names_to_collectors.get(name)
    if existing is not None:
        return existing
    return metric_cls(name, documentation, **kwargs)


RAG_REQUESTS: Counter = _get_or_create(
    Counter,
    "rag_requests_total",
    "Total RAG requests",
    labelnames=["status"],
)

RAG_REQUEST_LATENCY: Histogram = _get_or_create(
    Histogram,
    "rag_request_duration_seconds",
    "RAG request duration in seconds",
)

RAG_RETRIEVED_CHUNKS: Histogram = _get_or_create(
    Histogram,
    "rag_retrieved_chunks",
    "Number of chunks retrieved per request",
)

LLM_ERRORS: Counter = _get_or_create(
    Counter,
    "rag_llm_errors_total",
    "Total LLM request failures",
)
