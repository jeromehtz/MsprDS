"""
Tests d'intégration — endpoints Trajets (API + base de données + sécurité JWT).

Couvre la protection des routes, la création et la lecture des trajets,
et la persistance effective en base.
"""

import pytest
from models.trajet import Trajet

pytestmark = pytest.mark.integration


TRAJET = {
    "year": 2024,
    "origin_station_name": "Paris Gare de Lyon",
    "destination_station_name": "Lyon Part-Dieu",
    "origin_city": "Paris",
    "destination_city": "Lyon",
    "origin_region": "Ile-de-France",
    "destination_region": "Auvergne-Rhone-Alpes",
    "passengers_millions": 12.5,
    "type": "day",
    "source": "SNCF",
}


def test_get_trajets_requires_authentication(client):
    res = client.get("/trajets/")
    assert res.status_code == 401


def test_create_trajets_requires_authentication(client):
    res = client.post("/trajets/", json=TRAJET)
    assert res.status_code == 401


def test_get_trajets_empty_with_auth(client, auth_headers):
    res = client.get("/trajets/", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_create_then_list_trajet(client, auth_headers, db_session):
    create = client.post("/trajets/", json=TRAJET, headers=auth_headers)
    assert create.status_code == 200
    assert create.json() == {"message": "Trajet créé"}

    # Persistance vérifiée directement en base
    count = db_session.query(Trajet).count()
    assert count == 1

    # ...et exposé par l'API
    listing = client.get("/trajets/", headers=auth_headers)
    assert listing.status_code == 200
    data = listing.json()
    assert len(data) == 1
    assert data[0]["origin_station_name"] == "Paris Gare de Lyon"
    assert data[0]["passengers_millions"] == 12.5


def test_get_trajets_rejects_invalid_token(client):
    res = client.get("/trajets/", headers={"Authorization": "Bearer faux-token"})
    assert res.status_code == 401


# ── Filtrage ────────────────────────────────────────────────────────────────

def _seed(client, headers, **overrides):
    payload = {**TRAJET, **overrides}
    assert client.post("/trajets/", json=payload, headers=headers).status_code == 200


def test_filters_endpoint_lists_distinct_values(client, auth_headers):
    _seed(client, auth_headers, year=2023, type="TGV/Intercités")
    _seed(client, auth_headers, year=2024, type="TER/Intercités",
          destination_station_name="Dijon")

    res = client.get("/trajets/filters", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert 2023 in body["years"] and 2024 in body["years"]
    assert "TGV/Intercités" in body["service_types"]
    assert "TER/Intercités" in body["service_types"]


def test_filter_by_year(client, auth_headers):
    _seed(client, auth_headers, year=2023)
    _seed(client, auth_headers, year=2024, destination_station_name="Dijon")

    res = client.get("/trajets/", params={"year": 2023}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["year"] == 2023


def test_filter_by_service_type_and_region(client, auth_headers):
    _seed(client, auth_headers, type="TGV/Intercités", origin_region="Ile-de-France")
    _seed(client, auth_headers, type="TER/Intercités", origin_region="Bretagne",
          destination_station_name="Brest")

    res = client.get("/trajets/", params={"service_type": "TER/Intercités"}, headers=auth_headers)
    assert len(res.json()) == 1

    res2 = client.get("/trajets/", params={"origin_region": "Bretagne"}, headers=auth_headers)
    assert len(res2.json()) == 1


def test_filter_by_search_on_station_name(client, auth_headers):
    _seed(client, auth_headers, destination_station_name="Marseille St-Charles")
    _seed(client, auth_headers, destination_station_name="Dijon Ville")

    res = client.get("/trajets/", params={"search": "marseille"}, headers=auth_headers)
    assert len(res.json()) == 1
    assert "Marseille" in res.json()[0]["destination_station_name"]


def test_filter_limit(client, auth_headers):
    for i in range(5):
        _seed(client, auth_headers, destination_station_name=f"Gare {i}")
    res = client.get("/trajets/", params={"limit": 3}, headers=auth_headers)
    assert len(res.json()) == 3
