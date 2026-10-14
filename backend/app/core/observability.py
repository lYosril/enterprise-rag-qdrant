import logging
import time
from contextlib import contextmanager
from typing import Any

from prometheus_client import REGISTRY, Counter, Histogram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("enterprise_rag")


def _get_or_create(metric_cls, name: str, documentation: str, **kwargs) -> Any:
    """Return an existing registered metric or create a new one.

    Prevents ``DuplicateTimeseries`` errors when the module is imported more
    than once (e.g. during pytest collection with non-standard sys.path).
    """
    # prometheus_client stores collectors in _names_to_collectors keyed by name
    existing = REGISTRY._names_to_collectors.get(name)
    if existing is not None:
        return existing
    return metric_cls(name, documentation, **kwargs)


CHAT_REQUESTS: Counter = _get_or_create(
    Counter,
    "rag_chat_requests_total",
    "Total chat requests",
    labelnames=["status"],
)
CHAT_LATENCY: Histogram = _get_or_create(
    Histogram,
    "rag_chat_request_duration_seconds",
    "End-to-end chat request duration",
)
RETRIEVAL_LATENCY: Histogram = _get_or_create(
    Histogram,
    "rag_retrieval_duration_seconds",
    "Qdrant retrieval duration",
)
RERANK_LATENCY: Histogram = _get_or_create(
    Histogram,
    "rag_rerank_duration_seconds",
    "Cross-encoder reranking duration",
)
LLM_LATENCY: Histogram = _get_or_create(
    Histogram,
    "rag_llm_duration_seconds",
    "LLM request duration",
)
EMPTY_RETRIEVAL_TOTAL: Counter = _get_or_create(
    Counter,
    "rag_empty_retrieval_total",
    "Chat requests where retrieval returned no usable chunks",
)
LLM_TIMEOUT_TOTAL: Counter = _get_or_create(
    Counter,
    "rag_llm_timeout_total",
    "LLM requests that timed out",
)
LLM_TOKENS_TOTAL: Counter = _get_or_create(
    Counter,
    "rag_llm_tokens_total",
    "LLM token usage when reported by provider",
    labelnames=["kind"],
)
RETRIEVED_CHUNKS: Histogram = _get_or_create(
    Histogram,
    "rag_retrieved_chunks_count",
    "Number of chunks passed to the LLM after retrieval/rerank",
    buckets=(0, 1, 2, 3, 4, 5, 10, 20),
)

# Agent-specific metrics (Milestone 6)
AGENT_REQUESTS_TOTAL: Counter = _get_or_create(
    Counter,
    "rag_agent_requests_total",
    "Total agent requests by status and outcome",
    labelnames=["status", "outcome"],
)
AGENT_RETRIEVAL_ATTEMPTS: Histogram = _get_or_create(
    Histogram,
    "rag_agent_retrieval_attempts",
    "Number of retrieval attempts per request",
    buckets=(1, 2, 3),
)
AGENT_QUERY_REWRITES_TOTAL: Counter = _get_or_create(
    Counter,
    "rag_agent_query_rewrites_total",
    "Total query rewrites performed",
    labelnames=["outcome"],
)


def log_agent_turn(
    query_id: str,
    attempt_count: int,
    selected_source_ids: list[str],
    latency_seconds: float,
    outcome: str,
    token_usage: dict | None = None,
) -> None:
    """
    Structured logging of agent execution without leaking sensitive document
    content, user secrets, or authentication tokens.
    """
    logger.info(
        "AGENT_TURN query_id=%s attempts=%d sources=%s latency=%.3fs outcome=%s tokens=%s",
        query_id,
        attempt_count,
        selected_source_ids,
        latency_seconds,
        outcome,
        token_usage or {},
    )


class Timer:
    """Wall-clock timer for structured logs and optional Prometheus histograms."""

    def __init__(
        self,
        name: str,
        histogram: Histogram | None = None,
    ):
        self.name = name
        self.histogram = histogram
        self.elapsed_seconds: float = 0.0

    def __enter__(self):
        self._started_at = time.perf_counter()
        if self.histogram is not None:
            self._prometheus = self.histogram.time()
            self._prometheus.__enter__()
        else:
            self._prometheus = None
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._prometheus is not None:
            self._prometheus.__exit__(exc_type, exc, tb)
        self.elapsed_seconds = time.perf_counter() - self._started_at
        logger.info(
            "%s completed in %.3fs",
            self.name,
            self.elapsed_seconds,
        )
        return False


@contextmanager
def track_chat_request():
    with CHAT_LATENCY.time():
        try:
            yield
            CHAT_REQUESTS.labels(status="success").inc()
        except Exception:
            CHAT_REQUESTS.labels(status="error").inc()
            raise
