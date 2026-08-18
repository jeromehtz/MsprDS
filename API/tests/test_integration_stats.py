"""Tests d'intégration — endpoint KPI (API + agrégations base de données)."""

import pytest
from models.trajet import Trajet

pytestmark = pytest.mark.integration


def _make_trajet(**kw):
    base = dict(
        year=2024,
        origin_station_name="Paris Gare de Lyon",
        destination_station_name="Lyon Part-Dieu",
        origin_city="Paris",
        destination_city="Lyon",
        origin_region="Ile-de-France",
        destination_region="Auvergne-Rhone-Alpes",
        passengers_millions=10.0,
        type="TGV/Intercités",
        source="SNCF",
    )
    base.update(kw)
    return Trajet(**base)


def test_kpi_requires_auth(client):
    assert client.get("/stats/kpi").status_code == 401


def test_kpi_empty_dataset(client, auth_headers):
    res = client.get("/stats/kpi", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total_passengers_millions"] == 0
    assert body["nb_routes"] == 0


def test_kpi_aggregates(client, auth_headers, db_session):
    db_session.add_all([
        _make_trajet(year=2023, passengers_millions=5.0, type="TGV/Intercités"),
        _make_trajet(year=2024, passengers_millions=7.0, type="TGV/Intercités",
                     destination_station_name="Marseille St-Charles"),
        _make_trajet(year=2024, passengers_millions=3.0, type="TER/Intercités",
                     destination_station_name="Dijon"),
    ])
    db_session.commit()

    body = client.get("/stats/kpi", headers=auth_headers).json()
    assert body["total_passengers_millions"] == pytest.approx(15.0)
    assert body["nb_routes"] == 3
    assert body["years_covered"] == [2023, 2024]
    # Répartition par type de service
    assert body["by_service_type"]["TGV/Intercités"] == pytest.approx(12.0)
    assert body["by_service_type"]["TER/Intercités"] == pytest.approx(3.0)
    # Évolution annuelle
    assert body["by_year"]["2024"] == pytest.approx(10.0)
    # Top axes triés par volume décroissant
    assert body["top_routes"][0]["passengers_millions"] >= body["top_routes"][-1]["passengers_millions"]
    # Répartition jour/nuit : tous les services de test sont des services de jour
    assert body["by_period"]["Jour"] == pytest.approx(15.0)
    assert body["by_period"]["Nuit"] == pytest.approx(0.0)


def test_kpi_classifies_night_service(client, auth_headers, db_session):
    db_session.add_all([
        _make_trajet(type="TGV/Intercités", passengers_millions=8.0),
        _make_trajet(type="Intercités de Nuit", passengers_millions=2.0,
                     destination_station_name="Briançon"),
    ])
    db_session.commit()

    body = client.get("/stats/kpi", headers=auth_headers).json()
    assert body["by_period"]["Jour"] == pytest.approx(8.0)
    assert body["by_period"]["Nuit"] == pytest.approx(2.0)
