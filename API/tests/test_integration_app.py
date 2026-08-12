"""Tests d'intégration — endpoints applicatifs transverses (racine, monitoring)."""

import pytest

pytestmark = pytest.mark.integration


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"message": "API MSPR RUNNING"}


def test_metrics_endpoint_exposes_prometheus(client):
    # Génère au moins une requête mesurée par le middleware
    client.get("/")
    res = client.get("/metrics")
    assert res.status_code == 200
    # Format d'exposition Prometheus
    assert "api_requests_total" in res.text


def test_openapi_docs_available(client):
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert res.json()["info"]["title"] == "API MSPR"
