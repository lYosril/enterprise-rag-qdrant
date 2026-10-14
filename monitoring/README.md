# Monitoring & Observability Architecture

This directory contains the operational observability setup for the Enterprise RAG Assistant.

## Metrics Overview

The application exposes standard Prometheus metrics at `/metrics` using `prometheus_client.make_asgi_app()`.

### Key Metrics Exposed

| Metric Name | Type | Labels | Description |
|---|---|---|---|
| `rag_requests_total` | Counter | `status` (`success`, `error`) | Total API RAG requests handled. |
| `rag_request_duration_seconds` | Histogram | - | End-to-end RAG request latency in seconds. |
| `rag_retrieved_chunks` | Histogram | - | Number of chunks retrieved per query. |
| `rag_retrieval_duration_seconds` | Histogram | - | Qdrant retrieval duration. |
| `rag_rerank_duration_seconds` | Histogram | - | Cross-encoder reranking latency. |
| `rag_llm_duration_seconds` | Histogram | - | LLM completion call duration. |
| `rag_llm_errors_total` | Counter | - | Total LLM request failures. |
| `rag_llm_timeout_total` | Counter | - | Total LLM requests that timed out. |
| `rag_llm_tokens_total` | Counter | `kind` (`prompt`, `completion`) | Total LLM tokens processed. |
| `rag_agent_retrieval_attempts` | Histogram | - | Number of retrieval attempts per request. |
| `rag_agent_query_rewrites_total` | Counter | `outcome` (`rewritten`, `unchanged`, `timeout`, `error`) | Count of query rewrites performed. |

### Low-Cardinality Guardrails
To avoid high memory usage and cardinality explosions:
- Document names, filenames, user IDs, raw user queries, and auth tokens are **NEVER** used as Prometheus labels.
- Per-query traces and fine-grained identifiers are logged via `structlog` as structured JSON events instead.

---

## Prometheus Scrape Configuration

Add the following job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "enterprise_rag_backend"
    scrape_interval: 15s
    static_configs:
      - targets: ["backend:8000"]
    metrics_path: "/metrics"
```

---

## Grafana Dashboard Import

1. Open your Grafana instance (`http://localhost:3000`).
2. Navigate to **Dashboards** > **Import**.
3. Upload `monitoring/grafana_dashboard.json`.
4. Select your Prometheus data source and click **Import**.
