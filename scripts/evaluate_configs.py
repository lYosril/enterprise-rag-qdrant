"""
Milestone 9 — RAG retrieval-configuration benchmark (Experiments A–D).

This script benchmarks four retrieval configurations on an identical set of
questions and source documents:

    A — Baseline      : dense retrieval, top 5
    B — Reranking     : dense retrieval, top 20 candidates, reranked to top 5
    C — Hybrid        : dense + lexical (BM25) merged with Reciprocal Rank Fusion, top 5
    D — Hybrid+Rerank : hybrid candidates reranked to top 5

It measures Recall@5, MRR, answer correctness, citation validity, abstention
quality, latency, and cost, and writes a JSON summary plus a Markdown report.

Design notes
------------
* Dense retrieval uses the project's own embedding model and exact cosine
  similarity over the same chunks Qdrant stores in production. Qdrant's HNSW
  index returns the same nearest neighbours for a corpus of this size.
* Lexical retrieval uses the project's tokenizer and BM25 (rank_bm25), the same
  algorithm used by app.services.lexical_retrieval.
* Reranking and Reciprocal Rank Fusion call the project's own
  app.services.reranker.rerank_chunks and
  app.services.hybrid_retrieval.reciprocal_rank_fusion.
* Answer generation uses the project's system prompt and evidence formatter and
  the real resilient LLM client (app.services.llm_client.chat_completion).
* Nothing here invents results: every number is produced by an actual run and,
  when a configuration performs worse, that is reported as-is.

Usage::

    python scripts/evaluate_configs.py \
        --dataset backend/evaluation/benchmark_questions.json \
        --output-dir results

Use ``--retrieval-only`` to skip all LLM calls (retrieval metrics only).
"""

import argparse
import hashlib
import json
import logging
import re
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(BACKEND / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_configs")

from rank_bm25 import BM25Okapi  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.document_service import (  # noqa: E402
    embedding_model,
    make_deterministic_chunk_id,
    split_text,
)
from app.services.hybrid_retrieval import reciprocal_rank_fusion  # noqa: E402
from app.services.lexical_retrieval import _tokenize  # noqa: E402
from app.services.llm_client import chat_completion  # noqa: E402
from app.services.rag_service import (  # noqa: E402
    MULTI_DOC_SYSTEM_PROMPT,
    format_grouped_context,
)
from app.services.reranker import rerank_chunks  # noqa: E402


ABSTAIN_TEXT = (
    "I couldn't find sufficient evidence in the provided documents "
    "to answer that question."
)

ABSTENTION_INDICATORS = [
    "couldn't find",
    "could not find",
    "cannot find",
    "can't find",
    "unable to find",
    "sufficient evidence",
    "not found in",
    "not provided",
    "not available",
    "no information",
    "does not contain",
    "do not contain",
    "not mentioned",
    "isn't mentioned",
    "is not mentioned",
    "no mention",
    "not specified",
]

CONFIGS = {
    "A_dense_top5": {"label": "A — Dense top-5 (baseline)", "hybrid": False, "rerank": False},
    "B_dense_rerank_top5": {"label": "B — Dense top-20 rerank to top-5", "hybrid": False, "rerank": True},
    "C_hybrid_rrf_top5": {"label": "C — Hybrid (dense+BM25 RRF) top-5", "hybrid": True, "rerank": False},
    "D_hybrid_rerank_top5": {"label": "D — Hybrid top-20 rerank to top-5", "hybrid": True, "rerank": True},
}


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------
@dataclass
class Corpus:
    chunks: list[dict]
    matrix: np.ndarray
    documents: list[str]
    valid_citations: set[tuple[str, int]] = field(default_factory=set)


# A document whose entire stem is a UUID (as produced by the upload API) is an
# opaque duplicate of the same file stored under a human-readable name. When two
# byte-identical files exist, prefer the readable name so citations and reports
# stay meaningful.
_OPAQUE_NAME = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _corpus_sort_key(path: Path) -> tuple[bool, str]:
    return (bool(_OPAQUE_NAME.match(path.stem)), path.name.lower())


def load_corpus(documents_dir: Path) -> Corpus:
    """Load every PDF (de-duplicated by sha256) and split it into chunks."""
    pdf_paths = sorted(documents_dir.glob("*.pdf"), key=_corpus_sort_key)
    if not pdf_paths:
        raise SystemExit(f"No PDF documents found in {documents_dir}")

    seen_hashes: dict[str, str] = {}
    unique_paths: list[Path] = []
    skipped: list[str] = []
    for path in pdf_paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen_hashes:
            skipped.append(f"{path.name} (duplicate of {seen_hashes[digest]})")
            continue
        seen_hashes[digest] = path.name
        unique_paths.append(path)

    chunks: list[dict] = []
    documents: list[str] = []
    for path in unique_paths:
        documents.append(path.name)
        document_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, path.name))
        reader = PdfReader(str(path))
        for page_number, page in enumerate(reader.pages, start=1):
            text = " ".join((page.extract_text() or "").split())
            if not text:
                continue
            for idx, chunk_text in enumerate(split_text(text)):
                chunk_id = make_deterministic_chunk_id(
                    document_id, page_number, idx, version=1
                )
                chunks.append({
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "document": path.name,
                    "page": page_number,
                    "text": chunk_text,
                })

    if not chunks:
        raise SystemExit("No extractable text found in the provided PDFs.")

    logger.info(
        "Loaded %d chunks from %d document(s); skipped %d duplicate(s)",
        len(chunks), len(unique_paths), len(skipped),
    )
    for s in skipped:
        logger.info("  duplicate skipped: %s", s)

    vectors = embedding_model.encode(
        [c["text"] for c in chunks],
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )
    matrix = np.asarray(vectors, dtype=np.float32)
    valid = {(c["document"], c["page"]) for c in chunks}
    return Corpus(chunks=chunks, matrix=matrix, documents=documents, valid_citations=valid)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
class Retriever:
    def __init__(self, corpus: Corpus):
        self.corpus = corpus
        self.bm25 = BM25Okapi([_tokenize(c["text"]) for c in corpus.chunks])
        self.chunk_by_id = {c["chunk_id"]: c for c in corpus.chunks}

    def _row(self, index: int, score: float) -> dict:
        chunk = self.corpus.chunks[index]
        return {
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "document": chunk["document"],
            "page": chunk["page"],
            "text": chunk["text"],
            "score": float(score),
        }

    def dense(self, question: str, k: int) -> list[dict]:
        query_vector = embedding_model.encode(
            question, normalize_embeddings=True
        ).astype(np.float32)
        scores = self.corpus.matrix @ query_vector
        order = np.argsort(-scores)[:k]
        return [self._row(int(i), float(scores[i])) for i in order]

    def lexical(self, question: str, k: int) -> list[dict]:
        scores = self.bm25.get_scores(_tokenize(question))
        order = np.argsort(-scores)
        results: list[dict] = []
        for i in order:
            if float(scores[i]) <= 0:
                continue
            results.append(self._row(int(i), float(scores[i])))
            if len(results) >= k:
                break
        return results


def _normalize(items: list[dict], score_key: str) -> list[dict]:
    normalized = []
    for item in items:
        normalized.append({
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "document": item["document"],
            "page": item["page"],
            "text": item["text"],
            "score": float(item.get(score_key, item.get("score", 0.0))),
        })
    return normalized


def retrieve(
    retriever: Retriever,
    question: str,
    *,
    hybrid: bool,
    rerank: bool,
    candidate_limit: int = 20,
    final_top_k: int = 5,
) -> list[dict]:
    dense_candidates = retriever.dense(question, candidate_limit)

    if not hybrid:
        pool = dense_candidates
        if rerank and pool:
            return _normalize(rerank_chunks(question, pool, top_k=final_top_k), "rerank_score")
        return _normalize(pool[:final_top_k], "score")

    lexical_candidates = retriever.lexical(question, candidate_limit)
    dense_ranking = [c["chunk_id"] for c in dense_candidates]
    lexical_ranking = [c["chunk_id"] for c in lexical_candidates]
    rank_lists = [lst for lst in (dense_ranking, lexical_ranking) if lst]
    if not rank_lists:
        return []

    fused = reciprocal_rank_fusion(rank_lists, k=settings.rrf_k)
    candidate_map: dict[str, dict] = {}
    for item in dense_candidates + lexical_candidates:
        candidate_map.setdefault(item["chunk_id"], item)

    pool = []
    for chunk_id, rrf_score in fused[:candidate_limit]:
        if chunk_id not in candidate_map:
            continue
        merged = dict(candidate_map[chunk_id])
        merged["score"] = float(rrf_score)
        pool.append(merged)

    if not pool:
        return []
    if not rerank:
        return _normalize(pool[:final_top_k], "score")
    return _normalize(rerank_chunks(question, pool, top_k=final_top_k), "rerank_score")


# ---------------------------------------------------------------------------
# Metrics (pure helpers — unit tested)
# ---------------------------------------------------------------------------
def retrieval_metrics(
    sources: list[dict],
    expected_document: str | None,
    expected_pages: list[int],
    k: int = 5,
) -> tuple[float, bool, float]:
    """Return (page_recall@k, hit@k, reciprocal_rank) for one question.

    A retrieved source is relevant when its document matches the expected
    document and its page is one of the expected evidence pages.
    """
    if not expected_document or not expected_pages:
        return 0.0, False, 0.0

    matched_pages: set[int] = set()
    first_hit_rank = 0
    for rank, source in enumerate(sources[:k], start=1):
        doc = (source.get("document") or "").lower()
        page = source.get("page")
        if expected_document.lower() in doc and page in expected_pages:
            matched_pages.add(page)
            if first_hit_rank == 0:
                first_hit_rank = rank

    recall = len(matched_pages) / len(expected_pages)
    hit = len(matched_pages) > 0
    mrr = 1.0 / first_hit_rank if first_hit_rank else 0.0
    return recall, hit, mrr


def fact_coverage(answer: str, expected_facts: list[str]) -> float | None:
    if not expected_facts:
        return None
    answer_lower = (answer or "").lower()
    found = sum(1 for fact in expected_facts if fact.lower() in answer_lower)
    return found / len(expected_facts)


def looks_abstained(answer: str) -> bool:
    answer_lower = (answer or "").lower()
    return any(indicator in answer_lower for indicator in ABSTENTION_INDICATORS)


def citation_structural_validity(
    sources: list[dict], valid_citations: set[tuple[str, int]]
) -> float:
    if not sources:
        return 1.0
    valid = sum(
        1 for s in sources
        if (s.get("document"), s.get("page")) in valid_citations
    )
    return valid / len(sources)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


# ---------------------------------------------------------------------------
# LLM generation and judging
# ---------------------------------------------------------------------------
JUDGE_SYSTEM_PROMPT = (
    "You are a strict, impartial evaluator of a retrieval-augmented QA system. "
    "You are given a question, whether it is answerable from the source "
    "documents, the reference answer, the system's answer, and the evidence "
    "passages that were retrieved. Judge ONLY against the evidence shown.\n\n"
    "Return STRICT JSON with exactly these keys:\n"
    '{"abstained": bool, "correctness": number, "citation_supported": number, '
    '"rationale": string}\n'
    "Rules:\n"
    "- abstained: true only if the answer clearly states the information is "
    "not present / cannot be found in the documents.\n"
    "- correctness: for answerable questions, 1 = fully correct and supported, "
    "0.5 = partially correct or missing key facts, 0 = wrong, contradicted, or "
    "unsupported. For unanswerable questions, 1 if the system abstained, else 0.\n"
    "- citation_supported: 1 if the retrieved evidence plausibly supports the "
    "claims the answer actually makes (or the answer abstains), else 0.\n"
    "Output JSON only, with no markdown fences."
)


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    return json.loads(cleaned[start:end + 1])


def generate_answer(question: str, sources: list[dict]) -> dict:
    if not sources:
        return {"answer": ABSTAIN_TEXT, "sources": [], "usage": {}, "error": None}
    context = format_grouped_context(sources)
    messages = [
        {"role": "system", "content": MULTI_DOC_SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"},
    ]
    try:
        text, usage = chat_completion(messages, return_usage=True)
        return {"answer": text, "sources": sources, "usage": usage or {}, "error": None}
    except Exception as exc:  # noqa: BLE001 - record and continue benchmarking
        logger.warning("Generation failed for %r: %s", question[:60], exc)
        return {"answer": "", "sources": sources, "usage": {}, "error": str(exc)}


def judge_answer(
    question: str,
    expected_answer: str,
    is_answerable: bool,
    answer: str,
    sources: list[dict],
) -> dict:
    evidence = "\n".join(
        f"[{s.get('document')} page {s.get('page')}] {(s.get('text') or '')[:400]}"
        for s in sources
    ) or "(no evidence retrieved)"
    payload = {
        "question": question,
        "answerable_from_documents": is_answerable,
        "reference_answer": expected_answer,
        "system_answer": answer,
        "retrieved_evidence": evidence,
    }
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload)},
    ]
    try:
        text, usage = chat_completion(messages, return_usage=True)
        verdict = _parse_json(text)
        return {
            "abstained": bool(verdict.get("abstained", False)),
            "correctness": float(verdict.get("correctness", 0.0)),
            "citation_supported": float(verdict.get("citation_supported", 0.0)),
            "rationale": str(verdict.get("rationale", ""))[:300],
            "usage": usage or {},
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Judge failed for %r: %s", question[:60], exc)
        return {
            "abstained": looks_abstained(answer),
            "correctness": 0.0,
            "citation_supported": 0.0,
            "rationale": f"judge_error: {exc}",
            "usage": {},
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Evaluation driver
# ---------------------------------------------------------------------------
def _sum_usage(usage_a: dict, usage_b: dict) -> dict:
    def _get(d, key):
        try:
            return int(d.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0
    return {
        "prompt_tokens": _get(usage_a, "prompt_tokens") + _get(usage_b, "prompt_tokens"),
        "completion_tokens": _get(usage_a, "completion_tokens") + _get(usage_b, "completion_tokens"),
        "total_tokens": _get(usage_a, "total_tokens") + _get(usage_b, "total_tokens"),
    }


def evaluate_config(
    key: str,
    spec: dict,
    retriever: Retriever,
    cases: list[dict],
    *,
    candidate_limit: int,
    final_top_k: int,
    workers: int,
    retrieval_only: bool,
) -> dict:
    logger.info("Running configuration %s (%s)", key, spec["label"])

    # 1. Retrieval (sequential and cheap).
    records = []
    for case in cases:
        t0 = time.perf_counter()
        sources = retrieve(
            retriever,
            case["question"],
            hybrid=spec["hybrid"],
            rerank=spec["rerank"],
            candidate_limit=candidate_limit,
            final_top_k=final_top_k,
        )
        retrieval_ms = (time.perf_counter() - t0) * 1000
        records.append({
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "is_answerable": case["is_answerable"],
            "expected_document": case.get("expected_document"),
            "expected_pages": case.get("expected_pages", []),
            "expected_facts": case.get("expected_facts", []),
            "expected_answer": case.get("expected_answer", ""),
            "sources": [
                {"document": s["document"], "page": s["page"], "score": s["score"]}
                for s in sources
            ],
            "retrieval_ms": retrieval_ms,
            "_sources_full": sources,
        })

    # 2. Generation (parallel).
    if not retrieval_only:
        def _gen(record):
            t0 = time.perf_counter()
            result = generate_answer(record["question"], record["_sources_full"])
            return record, result, (time.perf_counter() - t0) * 1000

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_gen, r) for r in records]
            for future in as_completed(futures):
                record, result, generation_ms = future.result()
                record["answer"] = result["answer"]
                record["generation_ms"] = generation_ms
                record["answer_usage"] = result["usage"]
                record["generation_error"] = result["error"]

        # 3. Judging (parallel).
        def _judge(record):
            verdict = judge_answer(
                record["question"],
                record["expected_answer"],
                record["is_answerable"],
                record.get("answer", ""),
                record["_sources_full"],
            )
            return record, verdict

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_judge, r) for r in records]
            for future in as_completed(futures):
                record, verdict = future.result()
                record["verdict"] = verdict
    else:
        for record in records:
            record["answer"] = ""
            record["generation_ms"] = 0.0
            record["answer_usage"] = {}
            record["verdict"] = {}

    # 4. Per-question metrics.
    for record in records:
        recall, hit, mrr = retrieval_metrics(
            record["sources"],
            record.get("expected_document"),
            record.get("expected_pages", []),
            k=final_top_k,
        )
        record["recall_at_5"] = recall
        record["hit_at_5"] = hit
        record["mrr"] = mrr

        verdict = record.get("verdict") or {}
        judge_abstained = bool(verdict.get("abstained", False))
        abstained = judge_abstained or looks_abstained(record.get("answer", ""))
        record["abstained"] = abstained

        if record["is_answerable"]:
            record["abstention_quality"] = 0.0 if abstained else 1.0
        else:
            record["abstention_quality"] = 1.0 if abstained else 0.0

        record["correctness"] = float(verdict.get("correctness", 0.0))
        record["fact_coverage"] = fact_coverage(
            record.get("answer", ""), record.get("expected_facts", [])
        )

        structural = citation_structural_validity(
            record["_sources_full"], retriever.corpus.valid_citations
        )
        support = float(verdict.get("citation_supported", 0.0)) if record["_sources_full"] else 1.0
        if not record["_sources_full"]:
            record["citation_validity"] = 1.0 if abstained else 0.0
        else:
            record["citation_validity"] = structural * support

        record["latency_s"] = (record["retrieval_ms"] + record["generation_ms"]) / 1000.0

        answer_usage = record.get("answer_usage") or {}
        judge_usage = (verdict.get("usage") or {}) if verdict else {}
        combined = _sum_usage(answer_usage, judge_usage)
        record["prompt_tokens"] = combined["prompt_tokens"]
        record["completion_tokens"] = combined["completion_tokens"]
        record["total_tokens"] = combined["total_tokens"]
        record["cost_usd"] = (
            combined["prompt_tokens"] / 1_000_000 * settings.llm_input_cost_per_1m
            + combined["completion_tokens"] / 1_000_000 * settings.llm_output_cost_per_1m
        )

    # 5. Aggregate.
    answerable = [r for r in records if r["is_answerable"]]
    unanswerable = [r for r in records if not r["is_answerable"]]

    def mean(rows, key):
        values = [r[key] for r in rows if r.get(key) is not None]
        return round(statistics.fmean(values), 4) if values else 0.0

    latencies = [r["latency_s"] for r in records]
    retrieval_latencies = [r["retrieval_ms"] / 1000.0 for r in records]
    generation_latencies = [r["generation_ms"] / 1000.0 for r in records]

    aggregate = {
        "label": spec["label"],
        "n_questions": len(records),
        "n_answerable": len(answerable),
        "n_unanswerable": len(unanswerable),
        "recall_at_5": mean(answerable, "recall_at_5"),
        "hit_rate_at_5": mean(answerable, "hit_at_5"),
        "mrr": mean(answerable, "mrr"),
        "answer_correctness": mean(records, "correctness"),
        "answer_correctness_answerable": mean(answerable, "correctness"),
        "fact_coverage": mean(answerable, "fact_coverage"),
        "citation_validity": mean(records, "citation_validity"),
        "abstention_quality": mean(unanswerable, "abstention_quality"),
        "abstention_quality_all": mean(records, "abstention_quality"),
        "latency_mean_s": round(statistics.fmean(latencies), 4) if latencies else 0.0,
        "latency_p50_s": round(percentile(latencies, 0.5), 4),
        "latency_p95_s": round(percentile(latencies, 0.95), 4),
        "retrieval_mean_s": round(statistics.fmean(retrieval_latencies), 4) if retrieval_latencies else 0.0,
        "generation_mean_s": round(statistics.fmean(generation_latencies), 4) if generation_latencies else 0.0,
        "mean_total_tokens": round(mean(records, "total_tokens"), 1),
        "mean_prompt_tokens": round(mean(records, "prompt_tokens"), 1),
        "mean_completion_tokens": round(mean(records, "completion_tokens"), 1),
        "total_cost_usd": round(sum(r["cost_usd"] for r in records), 6),
        "mean_cost_usd": round(mean(records, "cost_usd"), 6),
    }

    details = []
    for record in records:
        details.append({k: v for k, v in record.items() if not k.startswith("_")})

    return {"aggregate": aggregate, "per_question": details}


def _metric_rows(configs: dict) -> list[tuple[str, str]]:
    return [
        ("Questions", "n_questions"),
        ("Recall@5 (page coverage)", "recall_at_5"),
        ("Hit rate@5", "hit_rate_at_5"),
        ("MRR@5", "mrr"),
        ("Answer correctness (all)", "answer_correctness"),
        ("Answer correctness (answerable)", "answer_correctness_answerable"),
        ("Fact coverage (answerable)", "fact_coverage"),
        ("Citation validity", "citation_validity"),
        ("Abstention quality (unanswerable)", "abstention_quality"),
        ("Latency mean (s)", "latency_mean_s"),
        ("Latency p50 (s)", "latency_p50_s"),
        ("Latency p95 (s)", "latency_p95_s"),
        ("Retrieval mean (s)", "retrieval_mean_s"),
        ("Generation mean (s)", "generation_mean_s"),
        ("Mean total tokens", "mean_total_tokens"),
        ("Mean cost (USD)", "mean_cost_usd"),
        ("Total cost (USD)", "total_cost_usd"),
    ]


def build_markdown(summary: dict) -> str:
    configs = summary["configs"]
    keys = list(configs.keys())
    meta = summary["metadata"]

    lines = []
    lines.append("# RAG Retrieval Configuration Benchmark (Milestone 9)")
    lines.append("")
    lines.append(f"- Generated: {meta['generated_at']}")
    lines.append(f"- Dataset: `{meta['dataset']}` ({meta['n_questions']} questions)")
    lines.append(f"- Documents: {', '.join(meta['documents'])}")
    lines.append(f"- Chunks indexed: {meta['n_chunks']}")
    lines.append(f"- Embedding model: `{meta['embedding_model']}`")
    lines.append(f"- Reranker: `{meta['reranker_model']}`")
    lines.append(f"- LLM: `{meta['llm_model']}`")
    lines.append(
        f"- Candidate limits: dense={meta['dense_candidate_limit']}, "
        f"lexical={meta['lexical_candidate_limit']}, final_top_k={meta['final_top_k']}, "
        f"rrf_k={meta['rrf_k']}"
    )
    lines.append(
        f"- Cost rates: ${meta['input_cost_per_1m']}/1M input, "
        f"${meta['output_cost_per_1m']}/1M output"
    )
    if meta.get("retrieval_only"):
        lines.append("- **RETRIEVAL-ONLY RUN**: no LLM calls were made.")
    lines.append("")

    header = "| Metric | " + " | ".join(configs[k]["aggregate"]["label"] for k in keys) + " |"
    separator = "|" + "---|" * (len(keys) + 1)
    lines.append(header)
    lines.append(separator)
    for title, fieldname in _metric_rows(configs):
        cells = []
        for k in keys:
            value = configs[k]["aggregate"].get(fieldname, "")
            cells.append("" if value is None else str(value))
        lines.append(f"| {title} | " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## Experimental setup")
    lines.append("")
    lines.append("- **A — Baseline:** dense retrieval, top 5.")
    lines.append("- **B — Reranking:** dense top 20 candidates, cross-encoder reranked to top 5.")
    lines.append("- **C — Hybrid:** dense + BM25 lexical candidates merged with Reciprocal Rank Fusion, top 5.")
    lines.append("- **D — Hybrid + reranking:** hybrid candidates reranked with the cross-encoder to top 5.")
    lines.append("")
    lines.append("All four configurations used identical questions and identical source documents.")
    lines.append("")
    lines.append("## Metric definitions")
    lines.append("")
    lines.append("- **Recall@5:** fraction of expected evidence pages present in the top-5 retrieved sources (answerable questions).")
    lines.append("- **Hit rate@5:** fraction of answerable questions with at least one relevant source in the top 5.")
    lines.append("- **MRR@5:** mean reciprocal rank of the first relevant source.")
    lines.append("- **Answer correctness:** LLM judge score (0/0.5/1) against the reference answer and retrieved evidence.")
    lines.append("- **Fact coverage:** fraction of expected keyword facts present in the answer.")
    lines.append("- **Citation validity:** cited documents/pages exist in the corpus AND the judge confirms the evidence supports the answer.")
    lines.append("- **Abstention quality:** the system abstains on unanswerable questions and answers answerable ones.")
    lines.append("- **Latency/cost:** measured end-to-end per question; tokens and cost include the grading call.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark RAG retrieval configurations A–D.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "backend" / "evaluation" / "benchmark_questions.json")
    parser.add_argument("--documents", type=Path, default=ROOT / "data" / "documents")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--configs", type=str, default="A,B,C,D")
    parser.add_argument("--limit", type=int, default=0, help="Only run the first N questions (0 = all).")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--retrieval-only", action="store_true", help="Skip all LLM calls.")
    args = parser.parse_args()

    with open(args.dataset, "r", encoding="utf-8") as handle:
        cases = json.load(handle)
    if args.limit:
        cases = cases[: args.limit]

    corpus = load_corpus(args.documents)
    retriever = Retriever(corpus)

    selected = []
    for token in args.configs.split(","):
        token = token.strip().upper()
        for key in CONFIGS:
            if key.startswith(token):
                selected.append(key)
                break
    if not selected:
        raise SystemExit(f"No matching configurations for {args.configs!r}")

    configs_result = {}
    for key in selected:
        configs_result[key] = evaluate_config(
            key,
            CONFIGS[key],
            retriever,
            cases,
            candidate_limit=settings.rag_dense_candidate_limit,
            final_top_k=settings.agent_final_top_k,
            workers=args.workers,
            retrieval_only=args.retrieval_only,
        )

    summary = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset": str(args.dataset.relative_to(ROOT)) if args.dataset.is_relative_to(ROOT) else str(args.dataset),
            "n_questions": len(cases),
            "documents": corpus.documents,
            "n_chunks": len(corpus.chunks),
            "embedding_model": settings.embedding_model,
            "reranker_model": settings.cross_encoder_model,
            "llm_model": settings.llm_model,
            "dense_candidate_limit": settings.rag_dense_candidate_limit,
            "lexical_candidate_limit": settings.rag_lexical_candidate_limit,
            "final_top_k": settings.agent_final_top_k,
            "rrf_k": settings.rrf_k,
            "input_cost_per_1m": settings.llm_input_cost_per_1m,
            "output_cost_per_1m": settings.llm_output_cost_per_1m,
            "retrieval_only": args.retrieval_only,
        },
        "configs": configs_result,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "config_benchmark.json"
    md_path = args.output_dir / "config_benchmark.md"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(build_markdown(summary))

    # Console summary.
    keys = list(configs_result.keys())
    print("\n" + "=" * 100)
    print("RETRIEVAL CONFIGURATION BENCHMARK")
    print("=" * 100)
    header = f"{'Metric':<34}" + "".join(f"{k[:16]:>18}" for k in keys)
    print(header)
    print("-" * len(header))
    for title, fieldname in _metric_rows(configs_result):
        row = f"{title:<34}"
        for k in keys:
            value = configs_result[k]["aggregate"].get(fieldname, "")
            row += f"{str(value):>18}"
        print(row)
    print("=" * 100)
    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
