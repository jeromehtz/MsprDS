"""Tests unitaires — service d'inférence CO₂ XGBoost (ml/predictor.py)."""

import pytest

from ml.predictor import predict_co2, get_options

pytestmark = pytest.mark.unit


def test_get_options_structure():
    opt = get_options()
    assert len(opt["stations"]) > 0
    assert len(opt["service_types"]) > 0
    assert len(opt["jours_semaine"]) == 7
    assert opt["target"] == "emissions_train_g_km"
    # Métriques du modèle exposées
    assert "R2" in opt["metrics"]


def test_predict_returns_plausible_values():
    opt = get_options()
    result = predict_co2({
        "origin_station": opt["stations"][0],
        "destination_station": opt["stations"][1],
        "service_type": opt["service_types"][0],
        "year": 2024,
        "passengers_millions": 1.0,
        "heure": 9,
        "jour_semaine": "Monday",
        "mois": 6,
        "est_jour_ferie": 0,
    })
    # Le train doit émettre nettement moins que voiture / avion
    assert result["train_g_km"] >= 0
    assert result["car_g_km"] > result["train_g_km"]
    assert result["plane_g_km"] > result["train_g_km"]
    assert result["co2_saved_vs_car_g_km"] == pytest.approx(
        result["car_g_km"] - result["train_g_km"], abs=0.01
    )


def test_predict_with_distance_returns_totals():
    opt = get_options()
    result = predict_co2({
        "origin_station": opt["stations"][0],
        "destination_station": opt["stations"][1],
        "service_type": opt["service_types"][0],
        "distance_km": 500,
    })
    assert result["distance_km"] == 500
    # Total = g/km × km / 1000
    assert result["total_train_kg"] == pytest.approx(result["train_g_km"] * 500 / 1000, abs=0.01)
    assert result["total_plane_kg"] > result["total_train_kg"]
