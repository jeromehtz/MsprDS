"""Tests unitaires — hachage et vérification de mot de passe (auth/password_handler.py)."""

import pytest
from auth.password_handler import hash_password, verify_password

pytestmark = pytest.mark.unit


def test_hash_is_not_plaintext():
    hashed = hash_password("monMotDePasse")
    assert hashed != "monMotDePasse"
    assert isinstance(hashed, str)
    # bcrypt produit un hash préfixé $2b$ / $2a$
    assert hashed.startswith("$2")


def test_hash_is_salted_and_non_deterministic():
    # Deux hachages du même mot de passe diffèrent (sel aléatoire)
    assert hash_password("secret") != hash_password("secret")


def test_verify_password_success():
    hashed = hash_password("bonMotDePasse")
    assert verify_password("bonMotDePasse", hashed) is True


def test_verify_password_failure():
    hashed = hash_password("bonMotDePasse")
    assert verify_password("mauvaisMotDePasse", hashed) is False
