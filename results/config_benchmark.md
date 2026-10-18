# RAG Retrieval Configuration Benchmark (Milestone 9)

- Generated: 2026-10-16T14:14:37.802476+00:00
- Dataset: `backend\evaluation\benchmark_questions.json` (71 questions)
- Documents: employee_handbook.pdf
- Chunks indexed: 172
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- LLM: `openai/gpt-oss-120b`
- Candidate limits: dense=20, lexical=20, final_top_k=5, rrf_k=60
- Cost rates: $0.15/1M input, $0.6/1M output

| Metric | A — Dense top-5 (baseline) | B — Dense top-20 rerank to top-5 | C — Hybrid (dense+BM25 RRF) top-5 | D — Hybrid top-20 rerank to top-5 |
|---|---|---|---|---|
| Questions | 71 | 71 | 71 | 71 |
| Recall@5 (page coverage) | 0.9683 | 1.0 | 0.9841 | 1.0 |
| Hit rate@5 | 0.9841 | 1.0 | 1.0 | 1.0 |
| MRR@5 | 0.8743 | 0.9497 | 0.9656 | 0.9497 |
| Answer correctness (all) | 0.0141 | 0.0423 | 0.0141 | 0.0141 |
| Answer correctness (answerable) | 0.0159 | 0.0317 | 0.0 | 0.0159 |
| Fact coverage (answerable) | 0.1296 | 0.1085 | 0.0476 | 0.0899 |
| Citation validity | 0.0141 | 0.0423 | 0.0 | 0.0141 |
| Abstention quality (unanswerable) | 0.0 | 0.25 | 0.125 | 0.125 |
| Latency mean (s) | 3.5365 | 4.2243 | 3.7793 | 4.0007 |
| Latency p50 (s) | 3.684 | 4.2397 | 3.8091 | 3.991 |
| Latency p95 (s) | 3.8687 | 5.2288 | 4.0523 | 4.7386 |
| Retrieval mean (s) | 0.0119 | 0.4904 | 0.0136 | 0.3784 |
| Generation mean (s) | 3.5246 | 3.7339 | 3.7657 | 3.6224 |
| Mean total tokens | 291.3 | 306.2 | 205.0 | 280.4 |
| Mean cost (USD) | 0.0001 | 0.0001 | 0.0001 | 0.0001 |
| Total cost (USD) | 0.005488 | 0.005828 | 0.003871 | 0.005308 |

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
