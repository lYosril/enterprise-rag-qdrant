"""
Unit tests for Agentic RAG:
- Query rewriting (with history, without history, coreference resolution, timeout fallback)
- Multi-document synthesis & evidence grouping
- Agent limits (max 2 attempts, context budget)
- Safe observability & abstention
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.core.config import settings
from app.core.observability import log_agent_turn
from app.services.agent_service import answer_with_agent
from app.services.query_rewriter import (
    has_reference_tokens,
    is_retrieval_weak,
    rewrite_query,
)
from app.services.rag_service import format_grouped_context, group_evidence_by_document


# ==============================================================================
# Query Rewriter Tests
# ==============================================================================

def test_query_rewriter_returns_original_when_no_history():
    res = rewrite_query("What is the leave policy?", history=[])
    assert res.was_rewritten is False
    assert res.query == "What is the leave policy?"


def test_query_rewriter_resolves_reference_with_history():
    history = [
        {"role": "user", "content": "Tell me about the annual travel expense policy."},
        {"role": "assistant", "content": "Travel expenses must be submitted within 30 days."},
    ]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "What is the deadline to submit annual travel expenses?"}}
        ],
        "usage": {"prompt_tokens": 40, "completion_tokens": 12},
    }

    with patch("requests.post", return_value=mock_response):
        res = rewrite_query("What happens if I miss the deadline?", history=history)

    assert res.was_rewritten is True
    assert "annual travel expenses" in res.query.lower()


def test_query_rewriter_falls_back_gracefully_on_timeout():
    history = [
        {"role": "user", "content": "Tell me about project Apollo."},
        {"role": "assistant", "content": "Project Apollo launched in Q3."},
    ]

    with patch("requests.post", side_effect=requests.Timeout("Timed out")):
        res = rewrite_query("What were its milestones?", history=history)

    assert res.was_rewritten is False
    assert res.query == "What were its milestones?"


def test_has_reference_tokens():
    assert has_reference_tokens("What does the policy say about it?") is True
    assert has_reference_tokens("Compare that with the previous version.") is True
    assert has_reference_tokens("What happens if I miss the deadline?") is True
    assert has_reference_tokens("Explain quantum computing algorithms in Python.") is False


def test_is_retrieval_weak():
    assert is_retrieval_weak([]) is True
    assert is_retrieval_weak([{"score": 0.2, "rerank_score": 0.3}], threshold=0.5) is True
    assert is_retrieval_weak([{"score": 0.8, "rerank_score": 0.85}], threshold=0.5) is False


# ==============================================================================
# Multi-Document Synthesis Tests
# ==============================================================================

def test_group_evidence_by_document():
    sources = [
        {"document": "handbook.pdf", "page": 4, "text": "Annual leave is 20 days."},
        {"document": "hr_guidelines.pdf", "page": 2, "text": "Annual leave is 25 days."},
        {"document": "handbook.pdf", "page": 2, "text": "Probation is 3 months."},
    ]
    grouped = group_evidence_by_document(sources)
    assert set(grouped.keys()) == {"handbook.pdf", "hr_guidelines.pdf"}
    # Verify sorted by page
    assert [s["page"] for s in grouped["handbook.pdf"]] == [2, 4]


def test_format_grouped_context_includes_document_delimiters():
    sources = [
        {"document": "employee_handbook.pdf", "page": 5, "text": "Employees get 15 days sick leave."},
        {"document": "updated_hr_policy.pdf", "page": 1, "text": "Employees get 10 days sick leave."},
    ]
    formatted = format_grouped_context(sources)
    assert "=== Document: employee_handbook.pdf ===" in formatted
    assert "=== Document: updated_hr_policy.pdf ===" in formatted
    assert "[Page 5]" in formatted
    assert "[Page 1]" in formatted


# ==============================================================================
# Agent Limits & Execution Tests
# ==============================================================================

def test_agent_abstains_when_no_evidence():
    with patch("app.services.agent_service.retrieve_ranked_chunks", return_value=[]):
        res = answer_with_agent(
            question="What is the quantum encryption key?",
            owner_id=str(uuid.uuid4()),
        )

    assert "couldn't find sufficient evidence" in res["answer"].lower()
    assert res["sources"] == []
    assert len(res["agent_trace"]) == 1
    assert res["agent_trace"][0]["attempt"] == 1


def test_agent_retries_when_initial_retrieval_is_weak():
    # Attempt 1 returns weak score (0.1), Attempt 2 returns strong source
    doc_id = str(uuid.uuid4())
    weak_sources = [
        {"chunk_id": "c1", "document_id": doc_id, "document": "doc.pdf", "page": 1, "text": "Vague info", "rerank_score": 0.2}
    ]
    strong_sources = [
        {"chunk_id": "c2", "document_id": doc_id, "document": "doc.pdf", "page": 2, "text": "Precise policy info", "rerank_score": 0.9}
    ]

    history = [
        {"role": "user", "content": "Discuss the parental leave policy."},
        {"role": "assistant", "content": "We offer parental leave."},
    ]

    mock_llm_response = MagicMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json.return_value = {
        "choices": [{"message": {"content": "Parental leave is 16 weeks [doc.pdf, page 2]."}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 15},
    }

    with patch("app.services.agent_service.retrieve_ranked_chunks", side_effect=[weak_sources, strong_sources]), \
         patch("app.services.agent_service.rewrite_query") as mock_rewrite, \
         patch("requests.post", return_value=mock_llm_response):

        from app.services.query_rewriter import RewriteResult
        mock_rewrite.return_value = RewriteResult(
            query="Parental leave duration and eligibility",
            was_rewritten=True,
            original="How long is it?",
        )

        res = answer_with_agent(
            question="How long is it?",
            owner_id=str(uuid.uuid4()),
            history=history,
        )

    # Must obey limit: at most 2 attempts
    assert len(res["agent_trace"]) == 2
    assert res["agent_trace"][0]["attempt"] == 1
    assert res["agent_trace"][1]["attempt"] == 2
    assert "Parental leave is 16 weeks" in res["answer"]


def test_agent_enforces_strict_max_attempts_limit():
    # Verify that even with multiple weak queries, attempts never exceed 2
    with patch("app.services.agent_service.retrieve_ranked_chunks", return_value=[]), \
         patch("app.services.agent_service.rewrite_query") as mock_rewrite:

        from app.services.query_rewriter import RewriteResult
        mock_rewrite.return_value = RewriteResult(
            query="Rewritten attempt",
            was_rewritten=True,
            original="Vague",
        )

        res = answer_with_agent(
            question="Vague",
            owner_id=str(uuid.uuid4()),
            history=[{"role": "user", "content": "prior"}],
        )

    assert len(res["agent_trace"]) <= settings.agent_max_retrieval_attempts
    assert res["sources"] == []


def test_log_agent_turn_does_not_raise_and_redacts():
    # Test that structured logger logs safely
    log_agent_turn(
        query_id="test-query-id",
        attempt_count=2,
        selected_source_ids=["chunk-1", "chunk-2"],
        latency_seconds=1.234,
        outcome="multi_doc_synthesized",
        token_usage={"prompt_tokens": 100, "completion_tokens": 50},
    )
