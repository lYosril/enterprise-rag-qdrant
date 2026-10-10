from unittest.mock import patch

from tests.conftest import (
    auth_headers,
    create_document_for_user,
    register,
    token_for,
    user_by_email,
)


def test_list_documents_returns_only_current_user_documents(client, db):
    register(client, "alice@example.com")
    register(client, "bob@example.com")

    alice = user_by_email(db, "alice@example.com")
    bob = user_by_email(db, "bob@example.com")
    create_document_for_user(db, alice, filename="alice-doc.pdf")
    create_document_for_user(db, bob, filename="bob-doc.pdf")

    token = token_for(client, "alice@example.com")
    response = client.get(
        "/api/v1/documents",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    documents = response.json()
    assert len(documents) == 1
    assert documents[0]["filename"] == "alice-doc.pdf"


def test_delete_other_users_document_returns_404(client, db):
    register(client, "alice@example.com")
    register(client, "bob@example.com")

    bob = user_by_email(db, "bob@example.com")
    bob_document = create_document_for_user(db, bob, filename="bob-only.pdf")

    alice_token = token_for(client, "alice@example.com")
    with patch("app.api.routes.delete_document_vectors"):
        response = client.delete(
            f"/api/v1/documents/{bob_document.id}",
            headers=auth_headers(alice_token),
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."

    remaining = client.get(
        "/api/v1/documents",
        headers=auth_headers(token_for(client, "bob@example.com")),
    )
    assert len(remaining.json()) == 1
