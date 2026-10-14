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


def test_upload_empty_pdf_returns_400(client, db):
    register(client, "alice@example.com")
    token = token_for(client, "alice@example.com")

    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers(token),
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_non_pdf_file_returns_400(client, db):
    register(client, "alice@example.com")
    token = token_for(client, "alice@example.com")

    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers(token),
        files={"file": ("script.sh", b"echo hi", "application/x-sh")},
    )
    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()


def test_retry_document_indexing(client, db):
    register(client, "alice@example.com")
    alice = user_by_email(db, "alice@example.com")
    doc = create_document_for_user(db, alice, filename="failed.pdf")
    doc.status = "failed"
    doc.error_message = "Temporary failure"
    db.commit()

    token = token_for(client, "alice@example.com")
    with patch("app.api.routes.index_document_task.delay"), \
         patch("app.api.routes.index_document"):
        response = client.post(
            f"/api/v1/documents/{doc.id}/retry",
            headers=auth_headers(token),
        )

    assert response.status_code == 200
    assert response.json()["status"] == "processing"

