"""Tests d'intégration — endpoints de prédiction CO₂ (API + modèle XGBoost + sécurité)."""

import pytest

pytestmark = pytest.mark.integration


def test_options_requires_auth(client):
    assert client.get("/predict/options").status_code == 401


def test_predict_requires_auth(client):
    res = client.post("/predict/co2", json={
        "origin_station": "Paris Gare de Lyon",
        "destination_station": "Lyon Part-Dieu",
        "service_type": "TGV/Intercités",
    })
    assert res.status_code == 401


def test_options_returns_lists(client, auth_headers):
    res = client.get("/predict/options", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["stations"], list) and body["stations"]
    assert isinstance(body["service_types"], list) and body["service_types"]


def test_predict_co2_returns_comparison(client, auth_headers):
    opt = client.get("/predict/options", headers=auth_headers).json()
    payload = {
        "origin_station": opt["stations"][0],
        "destination_station": opt["stations"][1],
        "service_type": opt["service_types"][0],
        "year": 2024,
        "distance_km": 400,
    }
    res = client.post("/predict/co2", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    for key in ("train_g_km", "car_g_km", "plane_g_km", "total_train_kg"):
        assert key in data
    assert data["car_g_km"] > data["train_g_km"]


def test_predict_validation_error_on_bad_hour(client, auth_headers):
    res = client.post("/predict/co2", json={
        "origin_station": "A", "destination_station": "B",
        "service_type": "X", "heure": 99,
    }, headers=auth_headers)
    assert res.status_code == 422  # validation Pydantic (heure 0..23)
