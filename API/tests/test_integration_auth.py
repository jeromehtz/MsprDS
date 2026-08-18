"""
Tests d'intégration — flux d'authentification de bout en bout (API + base de données).

Vérifie l'interopérabilité réelle entre les routers, SQLAlchemy et la base :
persistance des utilisateurs, hachage en base, et contrôle des identifiants.
"""

import pytest
from models.user import User

pytestmark = pytest.mark.integration


def test_register_persists_user_with_hashed_password(client, db_session):
    res = client.post("/auth/register", json={"username": "alice", "password": "secret123"})
    assert res.status_code == 200
    assert res.json() == {"message": "Utilisateur créé"}

    # L'utilisateur est bien présent en base...
    user = db_session.query(User).filter(User.username == "alice").first()
    assert user is not None
    # ...et le mot de passe est haché, jamais stocké en clair
    assert user.password != "secret123"
    assert user.role == "user"


def test_register_duplicate_username_is_rejected(client):
    payload = {"username": "bob", "password": "pwd"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 200

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400
    assert second.json()["detail"] == "Utilisateur déjà existant"


def test_login_success_returns_bearer_token(client, registered_user):
    res = client.post("/auth/login", json=registered_user)
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


def test_login_wrong_password_is_unauthorized(client, registered_user):
    res = client.post(
        "/auth/login",
        json={"username": registered_user["username"], "password": "mauvais"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Identifiants invalides"


def test_login_unknown_user_is_unauthorized(client):
    res = client.post("/auth/login", json={"username": "fantome", "password": "x"})
    assert res.status_code == 401
