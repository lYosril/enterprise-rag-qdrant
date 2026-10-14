
from prometheus_client import Counter, Histogram

RAG_REQUESTS = Counter(
    "rag_requests_total",
    "Total RAG requests",
    ["status"],
)

RAG_REQUEST_LATENCY = Histogram(
    "rag_request_duration_seconds",
    "RAG request duration in seconds",
)

RAG_RETRIEVED_CHUNKS = Histogram(
    "rag_retrieved_chunks",
    "Number of chunks retrieved per request",
)

LLM_ERRORS = Counter(
    "rag_llm_errors_total",
    "Total LLM request failures",
)
