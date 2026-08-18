"""Tests unitaires — résolution de l'utilisateur courant depuis un JWT (auth/dependencies.py)."""

import pytest
from fastapi import HTTPException

from auth.dependencies import get_current_user
from auth.jwt_handler import create_access_token

pytestmark = pytest.mark.unit


def test_get_current_user_returns_username_for_valid_token():
    token = create_access_token({"sub": "bob"})
    assert get_current_user(token) == "bob"


def test_get_current_user_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc:
        get_current_user("ceci-n-est-pas-un-jwt")
    assert exc.value.status_code == 401


def test_get_current_user_rejects_token_without_subject():
    token = create_access_token({"foo": "bar"})  # pas de "sub"
    with pytest.raises(HTTPException) as exc:
        get_current_user(token)
    assert exc.value.status_code == 401
