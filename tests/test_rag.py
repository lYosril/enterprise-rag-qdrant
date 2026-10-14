"""
Tests for RAG pipeline, resilient LLM client, and error handling.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests
from app.services.llm_client import LLMClientError, chat_completion
from app.services.rag_service import answer_question


def test_chat_completion_succeeds_normal_response():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Policy permits 20 days vacation."}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 10},
    }

    with patch("requests.post", return_value=mock_response):
        res = chat_completion([{"role": "user", "content": "What is the policy?"}])

    assert res == "Policy permits 20 days vacation."


def test_chat_completion_retries_transient_500_and_recovers():
    fail_response = MagicMock(status_code=500)
    fail_response.raise_for_status.side_effect = requests.HTTPError("Server Error", response=fail_response)

    ok_response = MagicMock(status_code=200)
    ok_response.json.return_value = {
        "choices": [{"message": {"content": "Recovered after server error."}}],
    }

    with patch("requests.post", side_effect=[fail_response, ok_response]), \
         patch("time.sleep") as mock_sleep:
        res = chat_completion([{"role": "user", "content": "hello"}], max_retries=2)

    assert res == "Recovered after server error."
    mock_sleep.assert_called_once()


def test_chat_completion_does_not_retry_permanent_400():
    bad_req = MagicMock(status_code=400)
    bad_req.raise_for_status.side_effect = requests.HTTPError("Bad Request", response=bad_req)

    with patch("requests.post", return_value=bad_req), \
         patch("time.sleep") as mock_sleep:
        with pytest.raises(LLMClientError) as excinfo:
            chat_completion([{"role": "user", "content": "invalid"}], max_retries=3)

    assert "Permanent LLM client error: HTTP 400" in str(excinfo.value)
    mock_sleep.assert_not_called()


def test_answer_question_abstains_when_sources_empty():
    res = answer_question("What is the quantum encryption secret?", owner_id="user1", custom_sources=[])
    assert "couldn't find relevant information" in res["answer"].lower()
    assert res["sources"] == []


def test_answer_question_propagates_controlled_error_on_llm_failure():
    sources = [{"document": "doc.pdf", "page": 1, "text": "Content"}]
    with patch("app.services.rag_service.chat_completion", side_effect=LLMClientError("LLM unavailable")):
        with pytest.raises(LLMClientError):
            answer_question("Question", owner_id="user1", custom_sources=sources)
