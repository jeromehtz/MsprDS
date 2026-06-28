from fastapi.testclient import TestClient
from API.main import app


def test_stats_volumes_default_country():
    client = TestClient(app)
    response = client.get("/stats/volumes?country=france")

    assert response.status_code == 200
    payload = response.json()
    assert payload["country"] == "france"
    assert isinstance(payload["top_stations"], list)
    assert isinstance(payload["train_vs_plane_comparison"], list)
    assert "top_train_vs_plane_saving" in payload


def test_stats_volumes_unknown_country():
    client = TestClient(app)
    response = client.get("/stats/volumes?country=unknown-country")

    assert response.status_code == 404
    assert "Aucun fichier de fréquentation disponible" in response.json()["detail"]
