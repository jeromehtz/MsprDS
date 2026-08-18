"""Tests unitaires — validation des schémas Pydantic (schemas/)."""

import pytest
from pydantic import ValidationError

from schemas.auth_schema import UserCreate, UserLogin, Token
from schemas.trajet_schema import TrajetCreate, TrajetResponse

pytestmark = pytest.mark.unit


def test_user_create_valid():
    u = UserCreate(username="alice", password="secret")
    assert u.username == "alice"
    assert u.password == "secret"


def test_user_create_missing_field():
    with pytest.raises(ValidationError):
        UserCreate(username="alice")  # password manquant


def test_token_schema():
    t = Token(access_token="abc", token_type="bearer")
    assert t.token_type == "bearer"


def test_trajet_create_valid():
    t = TrajetCreate(
        year=2024,
        origin_station_name="Paris Gare de Lyon",
        destination_station_name="Lyon Part-Dieu",
        origin_city="Paris",
        destination_city="Lyon",
        origin_region="Ile-de-France",
        destination_region="Auvergne-Rhone-Alpes",
        passengers_millions=12.5,
        type="day",
        source="SNCF",
    )
    assert t.year == 2024
    assert t.passengers_millions == 12.5


def test_trajet_create_wrong_type():
    with pytest.raises(ValidationError):
        TrajetCreate(
            year="pas-un-entier",
            origin_station_name="A",
            destination_station_name="B",
            origin_city="A",
            destination_city="B",
            origin_region="RA",
            destination_region="RB",
            passengers_millions="beaucoup",
            type="day",
            source="SNCF",
        )


def test_trajet_response_from_attributes():
    # TrajetResponse doit pouvoir être construit depuis un objet ORM-like
    class FakeORM:
        year = 2024
        origin_station_name = "A"
        destination_station_name = "B"
        origin_city = "A"
        destination_city = "B"
        origin_region = "RA"
        destination_region = "RB"
        passengers_millions = 1.0
        type = "day"
        source = "SNCF"

    resp = TrajetResponse.model_validate(FakeORM())
    assert resp.origin_station_name == "A"
