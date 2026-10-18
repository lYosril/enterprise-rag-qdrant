# RAG Retrieval Configuration Benchmark (Milestone 9)

- Generated: 2026-10-16T14:06:09.777370+00:00
- Dataset: `backend\evaluation\benchmark_questions.json` (2 questions)
- Documents: employee_handbook.pdf
- Chunks indexed: 172
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- LLM: `openai/gpt-oss-120b`
- Candidate limits: dense=20, lexical=20, final_top_k=5, rrf_k=60
- Cost rates: $0.15/1M input, $0.6/1M output

| Metric | A — Dense top-5 (baseline) |
|---|---|
| Questions | 2 |
| Recall@5 (page coverage) | 1.0 |
| Hit rate@5 | 1.0 |
| MRR@5 | 0.625 |
| Answer correctness (all) | 1.0 |
| Answer correctness (answerable) | 1.0 |
| Fact coverage (answerable) | 0.6667 |
| Citation validity | 1.0 |
| Abstention quality (unanswerable) | 0.0 |
| Latency mean (s) | 2.917 |
| Latency p50 (s) | 2.917 |
| Latency p95 (s) | 3.7037 |
| Retrieval mean (s) | 0.0147 |
| Generation mean (s) | 2.9023 |
| Mean total tokens | 3281.0 |
| Mean cost (USD) | 0.001 |
| Total cost (USD) | 0.00196 |

## Experimental setup

- **A — Baseline:** dense retrieval, top 5.
- **B — Reranking:** dense top 20 candidates, cross-encoder reranked to top 5.
- **C — Hybrid:** dense + BM25 lexical candidates merged with Reciprocal Rank Fusion, top 5.
- **D — Hybrid + reranking:** hybrid candidates reranked with the cross-encoder to top 5.

All four configurations used identical questions and identical source documents.

## Metric definitions

- **Recall@5:** fraction of expected evidence pages present in the top-5 retrieved sources (answerable questions).
- **Hit rate@5:** fraction of answerable questions with at least one relevant source in the top 5.
- **MRR@5:** mean reciprocal rank of the first relevant source.
- **Answer correctness:** LLM judge score (0/0.5/1) against the reference answer and retrieved evidence.
- **Fact coverage:** fraction of expected keyword facts present in the answer.
- **Citation validity:** cited documents/pages exist in the corpus AND the judge confirms the evidence supports the answer.
- **Abstention quality:** the system abstains on unanswerable questions and answers answerable ones.
- **Latency/cost:** measured end-to-end per question; tokens and cost include the grading call.
