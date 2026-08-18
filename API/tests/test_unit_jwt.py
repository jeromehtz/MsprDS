"""Tests unitaires — génération et décodage des JWT (auth/jwt_handler.py)."""

import os

import pytest
from jose import jwt
from auth.jwt_handler import create_access_token

pytestmark = pytest.mark.unit

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = os.environ["ALGORITHM"]


def test_token_is_a_string():
    token = create_access_token({"sub": "alice"})
    assert isinstance(token, str)
    assert token.count(".") == 2  # header.payload.signature


def test_token_contains_subject_and_expiry():
    token = create_access_token({"sub": "alice"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "alice"
    assert "exp" in payload


def test_token_signature_is_verified():
    token = create_access_token({"sub": "alice"})
    # Décoder avec une mauvaise clé doit échouer
    with pytest.raises(Exception):
        jwt.decode(token, "mauvaise-cle", algorithms=[ALGORITHM])
