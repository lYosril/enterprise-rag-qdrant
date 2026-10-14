"""
Tests for evaluation metrics and evaluation benchmark runner.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.evaluate_rag import (
    calculate_retrieval_metrics,
    evaluate_abstention,
    evaluate_answer_facts,
    evaluate_citations,
    run_evaluation,
)


def test_calculate_retrieval_metrics():
    sources = [
        {"document": "handbook.pdf", "page": 1},
        {"document": "handbook.pdf", "page": 4},
        {"document": "other.pdf", "page": 10},
    ]
    recall, mrr = calculate_retrieval_metrics(
        sources,
        expected_document="handbook.pdf",
        expected_pages=[4],
        k=5,
    )
    assert recall == 1.0
    # First hit at rank 2
    assert mrr == 0.5


def test_evaluate_answer_facts():
    answer = "The company equal opportunity policy ensures fair hiring."
    score = evaluate_answer_facts(answer, ["equal opportunity", "hiring", "stock"])
    assert round(score, 2) == 0.67


def test_evaluate_abstention():
    answer_abstain = "I couldn't find sufficient evidence in the provided documents."
    answer_fact = "The leave policy allows 20 days vacation."

    assert evaluate_abstention(answer_abstain, is_answerable=False) == 1.0
    assert evaluate_abstention(answer_fact, is_answerable=False) == 0.0
    assert evaluate_abstention(answer_fact, is_answerable=True) == 1.0
    assert evaluate_abstention(answer_abstain, is_answerable=True) == 0.0


def test_evaluate_citations():
    sources = [
        {"document": "doc1.pdf", "page": 3},
        {"document": "doc2.pdf", "page": 5},
    ]
    assert evaluate_citations(sources) == 1.0
    assert evaluate_citations([]) == 1.0


def test_evaluation_runner_end_to_end(tmp_path):
    dataset_file = tmp_path / "test_eval.json"
    dataset_file.write_text(
        """[
            {
                "id": "q1",
                "category": "single_document",
                "question": "What is the policy?",
                "history": [],
                "expected_document": "doc.pdf",
                "expected_pages": [1],
                "expected_facts": ["policy"],
                "is_answerable": true
            }
        ]""",
        encoding="utf-8",
    )
    output_file = tmp_path / "comparison.json"

    mock_baseline = {
        "answer": "The policy is standard.",
        "sources": [{"document": "doc.pdf", "page": 1, "chunk_id": "c1"}],
        "token_usage": {"total_tokens": 50},
    }
    mock_agent = {
        "answer": "The policy is standard.",
        "sources": [{"document": "doc.pdf", "page": 1, "chunk_id": "c1"}],
        "agent_trace": [{"attempt": 1}],
        "token_usage": {"total_tokens": 55},
    }

    with patch("scripts.evaluate_rag.answer_question", return_value=mock_baseline), \
         patch("scripts.evaluate_rag.answer_with_agent", return_value=mock_agent), \
         patch("scripts.evaluate_rag.SessionLocal"):

        summary = run_evaluation(dataset_file, output_file)

    assert "metrics" in summary
    assert "baseline" in summary["metrics"]
    assert "agentic" in summary["metrics"]
    assert output_file.exists()
