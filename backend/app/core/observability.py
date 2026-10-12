import logging
import time
from contextlib import contextmanager

from prometheus_client import Counter, Histogram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("enterprise_rag")

CHAT_REQUESTS = Counter(
    "rag_chat_requests_total",
    "Total chat requests",
    ["status"],
)
CHAT_LATENCY = Histogram(
    "rag_chat_request_duration_seconds",
    "End-to-end chat request duration",
)
RETRIEVAL_LATENCY = Histogram(
    "rag_retrieval_duration_seconds",
    "Qdrant retrieval duration",
)
RERANK_LATENCY = Histogram(
    "rag_rerank_duration_seconds",
    "Cross-encoder reranking duration",
)
LLM_LATENCY = Histogram(
    "rag_llm_duration_seconds",
    "LLM request duration",
)
EMPTY_RETRIEVAL_TOTAL = Counter(
    "rag_empty_retrieval_total",
    "Chat requests where retrieval returned no usable chunks",
)
LLM_TIMEOUT_TOTAL = Counter(
    "rag_llm_timeout_total",
    "LLM requests that timed out",
)
LLM_TOKENS_TOTAL = Counter(
    "rag_llm_tokens_total",
    "LLM token usage when reported by provider",
    ["kind"],
)
RETRIEVED_CHUNKS = Histogram(
    "rag_retrieved_chunks_count",
    "Number of chunks passed to the LLM after retrieval/rerank",
    buckets=(0, 1, 2, 3, 4, 5, 10, 20),
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
