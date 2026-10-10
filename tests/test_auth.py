from tests.conftest import VALID_PASSWORD, login, register


def test_register_new_user_returns_201(client):
    response = register(client, "alice@example.com")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert "id" in body


def test_register_duplicate_email_returns_409(client):
    register(client, "alice@example.com")
    response = register(client, "alice@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "An account with this email already exists."
    )


def test_login_with_incorrect_password_returns_401(client):
    register(client, "alice@example.com")
    response = login(client, "alice@example.com", "WrongPassword1!")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_protected_endpoint_without_token_returns_401(client):
    response = client.get("/api/v1/documents")

    assert response.status_code == 401
    assert "detail" in response.json()
