"""
Configuration commune des tests backend (pytest).

Stratégie :
- On force des variables d'environnement de test AVANT d'importer le code de
  l'application, car `database.py`, `auth/jwt_handler.py` et `auth/dependencies.py`
  lisent ces valeurs au moment de l'import (au niveau module).
- La base de données réelle (PostgreSQL) est remplacée par une base SQLite en
  mémoire dédiée aux tests, via l'override de la dépendance `get_db`.
- Chaque test repart d'un schéma propre (create_all / drop_all autour de chaque test).
"""

import os

# 1) Variables d'env de test — DOIVENT être définies avant tout import applicatif.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("ALGORITHM", "HS256")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Imports applicatifs (après avoir fixé l'environnement)
from database import Base, get_db
import models.user   # noqa: F401 — enregistre la table `users` sur Base.metadata
import models.trajet  # noqa: F401 — enregistre la table `trajets` sur Base.metadata
from main import app

# Moteur SQLite en mémoire partagé entre connexions (StaticPool) pour les tests.
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(autouse=True)
def _fresh_schema():
    """Recrée un schéma vierge avant chaque test et le nettoie après."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def db_session():
    """Session directe vers la base de test (tests unitaires / d'intégration DB)."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Client HTTP FastAPI avec la dépendance `get_db` redirigée vers SQLite."""
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    """Crée un utilisateur de test et renvoie ses identifiants."""
    creds = {"username": "tester", "password": "pwd12345"}
    client.post("/auth/register", json=creds)
    return creds


@pytest.fixture
def auth_token(client, registered_user):
    """Renvoie un JWT valide pour l'utilisateur de test."""
    res = client.post("/auth/login", json=registered_user)
    return res.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
