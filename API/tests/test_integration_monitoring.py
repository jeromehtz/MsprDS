"""Tests d'intégration — endpoints de monitoring (santé + synthèse incidents)."""

import pytest

pytestmark = pytest.mark.integration


def test_health_is_public_and_ok(client):
    res = client.get("/monitoring/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["api"] == "up"
    assert body["database"] == "up"


def test_summary_requires_auth(client):
    assert client.get("/monitoring/summary").status_code == 401


def test_summary_structure_and_counts(client, auth_headers):
    # Génère du trafic : un succès et une erreur (404)
    client.get("/")
    client.get("/route-inexistante")

    res = client.get("/monitoring/summary", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    for key in ("total_requests", "error_count", "error_rate_pct", "by_status", "incidents"):
        assert key in body
    assert body["total_requests"] >= 1
    # Le 404 doit être comptabilisé comme incident
    assert any("404" in k for k in body["by_status"])
    assert body["error_count"] >= 1
