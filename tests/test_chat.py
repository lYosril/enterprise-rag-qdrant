import uuid
from unittest.mock import patch

from tests.conftest import (
    auth_headers,
    create_conversation_with_messages,
    register,
    token_for,
    user_by_email,
)


def test_chat_returns_answer_and_sources_when_documents_exist(client):
    register(client, "alice@example.com")
    token = token_for(client, "alice@example.com")
    document_id = uuid.uuid4()

    rag_result = {
        "answer": "The policy allows remote work up to three days per week.",
        "sources": [
            {
                "document_id": str(document_id),
                "document": "handbook.pdf",
                "page": 4,
                "text": "Employees may work remotely up to three days weekly.",
                "score": 0.91,
            }
        ],
    }

    with patch(
        "app.api.routes.answer_question",
        return_value=rag_result,
    ) as mocked_rag:
        response = client.post(
            "/api/v1/chat",
            headers=auth_headers(token),
            json={"question": "What is the remote work policy?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == rag_result["answer"]
    assert len(body["sources"]) == 1
    assert body["sources"][0]["document"] == "handbook.pdf"
    assert body["sources"][0]["page"] == 4
    mocked_rag.assert_called_once()
    assert mocked_rag.call_args.kwargs["owner_id"]


def test_chat_without_indexed_documents_returns_safe_response(client):
    register(client, "alice@example.com")
    token = token_for(client, "alice@example.com")

    empty_rag_result = {
        "answer": (
            "I couldn't find relevant information "
            "in the provided documents."
        ),
        "sources": [],
    }

    with patch(
        "app.api.routes.answer_question",
        return_value=empty_rag_result,
    ):
        response = client.post(
            "/api/v1/chat",
            headers=auth_headers(token),
            json={"question": "What is the vacation policy?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "couldn't find relevant information" in body["answer"].lower()
    assert body["sources"] == []


def test_continue_another_users_conversation_is_rejected(client, db):
    register(client, "alice@example.com")
    register(client, "bob@example.com")

    bob = user_by_email(db, "bob@example.com")
    bob_conversation = create_conversation_with_messages(db, bob)

    alice_token = token_for(client, "alice@example.com")

    with patch(
        "app.api.routes.answer_question",
        return_value={"answer": "Should not run", "sources": []},
    ) as mocked_rag:
        response = client.post(
            "/api/v1/chat",
            headers=auth_headers(alice_token),
            json={
                "question": "Can I see Bob's history?",
                "conversation_id": str(bob_conversation.id),
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found."
    mocked_rag.assert_not_called()

    messages_response = client.get(
        f"/api/v1/conversations/{bob_conversation.id}/messages",
        headers=auth_headers(alice_token),
    )
    assert messages_response.status_code == 404
