import os
import sys
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

load_dotenv(ROOT / ".env")
load_dotenv(BACKEND / ".env")

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "pytest-jwt-secret-key-minimum-32-chars",
)
os.environ.setdefault("LLM_API_KEY", "pytest-llm-api-key")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Conversation, Document, Message, User  # noqa: E402

VALID_PASSWORD = "SecurePass123!"


@pytest.fixture(autouse=True)
def _clean_database():
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE messages, conversations, "
                "documents, users RESTART IDENTITY CASCADE"
            )
        )
    yield


@pytest.fixture
def client():
    with patch("app.main.ensure_collection"):
        with TestClient(app) as test_client:
            yield test_client


def register(client: TestClient, email: str, password: str = VALID_PASSWORD):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )


def login(client: TestClient, email: str, password: str = VALID_PASSWORD):
    return client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def token_for(client: TestClient, email: str) -> str:
    response = login(client, email)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def user_by_email(db, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    assert user is not None, f"Expected user {email} to exist"
    return user


def create_document_for_user(
    db,
    user: User,
    filename: str = "report-a.pdf",
) -> Document:
    document_id = uuid.uuid4()
    document = Document(
        id=document_id,
        filename=filename,
        stored_path=str(ROOT / "data" / "documents" / f"{document_id}.pdf"),
        status="indexed",
        chunk_count=2,
        owner_id=user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def create_conversation_with_messages(db, user: User) -> Conversation:
    conversation = Conversation(owner_id=user.id)
    db.add(conversation)
    db.flush()
    db.add_all([
        Message(
            conversation_id=conversation.id,
            role="user",
            content="Private question from user B",
            sources=[],
        ),
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content="Private answer that must not leak",
            sources=[],
        ),
    ])
    db.commit()
    db.refresh(conversation)
    return conversation


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
