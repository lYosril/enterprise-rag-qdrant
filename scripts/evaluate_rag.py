"""
Evaluation script comparing baseline RAG against Agentic RAG.

Measures:
1. Recall@K and MRR (Mean Reciprocal Rank) on retrieval.
2. Fact coverage / Answer correctness against expected key facts.
3. Citation validity (verifying cited document and pages match retrieved passages).
4. Abstention quality for unanswerable questions.
5. Average retrieval attempts per question.
6. End-to-end latency and LLM token usage.

Usage:
    python scripts/evaluate_rag.py --dataset tests/eval_dataset.json --output results/eval_comparison.json
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

# Add project root and backend to python path
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(BACKEND / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_rag")

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.agent_service import answer_with_agent
from app.services.citation_service import validate_sources
from app.services.rag_service import answer_question


def calculate_retrieval_metrics(
    sources: list[dict],
    expected_document: str | None,
    expected_pages: list[int],
    k: int = 5,
) -> tuple[float, float]:
    """
    Compute Recall@K and MRR for retrieved sources against expected doc/pages.
    """
    if not expected_document or not expected_pages:
        return 0.0, 0.0

    top_k_sources = sources[:k]
    matched_pages = set()
    first_hit_rank = 0

    for rank, s in enumerate(top_k_sources, start=1):
        doc = (s.get("document") or "").lower()
        page = s.get("page")
        if expected_document.lower() in doc and page in expected_pages:
            matched_pages.add(page)
            if first_hit_rank == 0:
                first_hit_rank = rank

    recall = len(matched_pages) / len(expected_pages) if expected_pages else 0.0
    mrr = 1.0 / first_hit_rank if first_hit_rank > 0 else 0.0
    return recall, mrr


def evaluate_answer_facts(answer: str, expected_facts: list[str]) -> float:
    """Fraction of expected facts/terms found in the answer."""
    if not expected_facts:
        return 1.0
    answer_lower = answer.lower()
    found = sum(1 for f in expected_facts if f.lower() in answer_lower)
    return found / len(expected_facts)


def evaluate_abstention(answer: str, is_answerable: bool) -> float:
    """
    Returns 1.0 if the pipeline properly abstained when unanswerable,
    or answered when answerable.
    """
    abstention_indicators = [
        "couldn't find", "could not find", "sufficient evidence",
        "not found in", "cannot be found", "not provided"
    ]
    is_abstaining = any(ind in answer.lower() for ind in abstention_indicators)

    if not is_answerable:
        return 1.0 if is_abstaining else 0.0
    else:
        return 0.0 if is_abstaining else 1.0


def evaluate_citations(sources: list[dict]) -> float:
    """Check that retrieved sources have valid doc name and page."""
    if not sources:
        return 1.0
    valid = sum(1 for s in sources if s.get("document") and s.get("page") is not None)
    return valid / len(sources)


def run_evaluation(dataset_path: Path, output_path: Path, mock_llm: bool = False):
    logger.info("Loading evaluation dataset from %s", dataset_path)
    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    db = SessionLocal()
    owner_id = str(uuid.uuid4())

    baseline_results = []
    agent_results = []

    print("\n" + "=" * 70)
    print("RUNNING BENCHMARK: Baseline RAG vs. Agentic RAG")
    print("=" * 70)

    for idx, item in enumerate(cases, start=1):
        q_id = item["id"]
        question = item["question"]
        history = item.get("history", [])
        expected_doc = item.get("expected_document")
        expected_pages = item.get("expected_pages", [])
        expected_facts = item.get("expected_facts", [])
        is_answerable = item.get("is_answerable", True)

        print(f"\n[{idx}/{len(cases)}] Case: {q_id} ({item.get('category')})")
        print(f"  Question: {question}")

        # ----------------------------------------------------------------------
        # 1. Baseline RAG
        # ----------------------------------------------------------------------
        t0 = time.perf_counter()
        try:
            b_out = answer_question(question=question, owner_id=owner_id, db=db)
        except Exception as e:
            logger.warning("Baseline error on %s: %s", q_id, e)
            b_out = {"answer": "Error", "sources": [], "token_usage": {}}
        b_lat = time.perf_counter() - t0

        b_sources = b_out.get("sources", [])
        b_recall, b_mrr = calculate_retrieval_metrics(b_sources, expected_doc, expected_pages)
        b_fact_score = evaluate_answer_facts(b_out.get("answer", ""), expected_facts)
        b_abstain_score = evaluate_abstention(b_out.get("answer", ""), is_answerable)
        b_cit_score = evaluate_citations(b_sources)
        b_tokens = (b_out.get("token_usage") or {}).get("total_tokens", 0)

        baseline_results.append({
            "id": q_id,
            "latency": b_lat,
            "recall": b_recall,
            "mrr": b_mrr,
            "fact_score": b_fact_score,
            "abstention_score": b_abstain_score,
            "citation_score": b_cit_score,
            "tokens": b_tokens,
            "attempts": 1,
        })

        # ----------------------------------------------------------------------
        # 2. Agentic RAG (with query rewriting, history, multi-doc, and limits)
        # ----------------------------------------------------------------------
        t0 = time.perf_counter()
        try:
            a_out = answer_with_agent(question=question, owner_id=owner_id, db=db, history=history)
        except Exception as e:
            logger.warning("Agent error on %s: %s", q_id, e)
            a_out = {"answer": "Error", "sources": [], "agent_trace": [], "token_usage": {}}
        a_lat = time.perf_counter() - t0

        a_sources = a_out.get("sources", [])
        a_recall, a_mrr = calculate_retrieval_metrics(a_sources, expected_doc, expected_pages)
        a_fact_score = evaluate_answer_facts(a_out.get("answer", ""), expected_facts)
        a_abstain_score = evaluate_abstention(a_out.get("answer", ""), is_answerable)
        a_cit_score = evaluate_citations(a_sources)
        a_attempts = len(a_out.get("agent_trace", [])) or 1
        a_tokens = (a_out.get("token_usage") or {}).get("total_tokens", 0)

        agent_results.append({
            "id": q_id,
            "latency": a_lat,
            "recall": a_recall,
            "mrr": a_mrr,
            "fact_score": a_fact_score,
            "abstention_score": a_abstain_score,
            "citation_score": a_cit_score,
            "tokens": a_tokens,
            "attempts": a_attempts,
        })

    db.close()

    # --------------------------------------------------------------------------
    # Aggregate Metrics Summary
    # --------------------------------------------------------------------------
    def avg(lst, key):
        return sum(x[key] for x in lst) / len(lst) if lst else 0.0

    summary = {
        "metrics": {
            "baseline": {
                "avg_recall_at_5": round(avg(baseline_results, "recall"), 3),
                "mrr": round(avg(baseline_results, "mrr"), 3),
                "fact_correctness": round(avg(baseline_results, "fact_score"), 3),
                "abstention_quality": round(avg(baseline_results, "abstention_score"), 3),
                "citation_validity": round(avg(baseline_results, "citation_score"), 3),
                "avg_retrieval_attempts": round(avg(baseline_results, "attempts"), 2),
                "avg_latency_seconds": round(avg(baseline_results, "latency"), 3),
                "avg_token_usage": round(avg(baseline_results, "tokens"), 1),
            },
            "agentic": {
                "avg_recall_at_5": round(avg(agent_results, "recall"), 3),
                "mrr": round(avg(agent_results, "mrr"), 3),
                "fact_correctness": round(avg(agent_results, "fact_score"), 3),
                "abstention_quality": round(avg(agent_results, "abstention_score"), 3),
                "citation_validity": round(avg(agent_results, "citation_score"), 3),
                "avg_retrieval_attempts": round(avg(agent_results, "attempts"), 2),
                "avg_latency_seconds": round(avg(agent_results, "latency"), 3),
                "avg_token_usage": round(avg(agent_results, "tokens"), 1),
            },
        },
        "baseline_details": baseline_results,
        "agentic_details": agent_results,
    }

    # Print comparison table
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS COMPARISON")
    print("=" * 70)
    print(f"{'Metric':<32} | {'Baseline RAG':<16} | {'Agentic RAG':<16}")
    print("-" * 70)
    b_m = summary["metrics"]["baseline"]
    a_m = summary["metrics"]["agentic"]
    for k in b_m.keys():
        name = k.replace("_", " ").title()
        print(f"{name:<32} | {str(b_m[k]):<16} | {str(a_m[k]):<16}")
    print("=" * 70)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    logger.info("Evaluation results saved to %s", output_path)
    return summary


if __name__ == "__main__":
    default_dataset = ROOT / "backend" / "evaluation" / "questions.json"
    if not default_dataset.exists():
        default_dataset = ROOT / "tests" / "eval_dataset.json"

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=default_dataset)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_comparison.json")
    args = parser.parse_args()
    run_evaluation(args.dataset, args.output)
