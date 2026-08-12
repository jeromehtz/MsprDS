"""
Test d'intégration MLflow — vérifie que le modèle journalisé dans MLflow puis
rechargé produit les mêmes prédictions que le .pkl local, et que le predictor sait
basculer sur MLflow via les variables d'environnement.

Utilise un tracking store local (fichier), sans serveur ni Model Registry.
"""

import pytest

pytestmark = pytest.mark.integration

mlflow = pytest.importorskip("mlflow")
import mlflow.xgboost  # noqa: E402

from ml import predictor  # noqa: E402


PAYLOAD = {
    "origin_station": "Paris Gare de Lyon",
    "destination_station": "Lyon Part-Dieu",
    "service_type": "TGV/Intercités",
    "year": 2024,
    "distance_km": 400,
}


def test_predictor_loads_model_from_mlflow(tmp_path, monkeypatch):
    # Backend SQLite (le file store est déprécié en MLflow 3.x)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"

    # 1) Prédiction de référence avec le modèle local (.pkl)
    monkeypatch.delenv("USE_MLFLOW", raising=False)
    predictor._model.cache_clear()
    # On aligne le payload sur des modalités réellement connues du modèle
    opt = predictor.get_options()
    payload = dict(PAYLOAD)
    payload["service_type"] = opt["service_types"][0]
    payload["origin_station"] = opt["stations"][0]
    payload["destination_station"] = opt["stations"][1]
    baseline = predictor.predict_co2(payload)["train_g_km"]

    # 2) Journalisation du modèle dans MLflow (tracking SQLite, artefacts en tmp)
    mlflow.set_tracking_uri(tracking_uri)
    exp_id = mlflow.create_experiment(
        "co2-test", artifact_location=(tmp_path / "artifacts").as_uri()
    )
    mlflow.set_experiment(experiment_id=exp_id)
    with mlflow.start_run():
        info = mlflow.xgboost.log_model(
            xgb_model=predictor._bundle()["model"], artifact_path="model"
        )

    # 3) Bascule du predictor sur MLflow
    monkeypatch.setenv("USE_MLFLOW", "true")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", tracking_uri)
    monkeypatch.setenv("MLFLOW_MODEL_URI", info.model_uri)
    predictor._model.cache_clear()

    via_mlflow = predictor.predict_co2(payload)["train_g_km"]

    # Les deux sources doivent donner la même prédiction
    assert via_mlflow == pytest.approx(baseline, abs=0.01)

    # Nettoyage : on restaure le cache pour les autres tests
    predictor._model.cache_clear()


def test_get_options_exposes_model_source(monkeypatch):
    monkeypatch.delenv("USE_MLFLOW", raising=False)
    assert predictor.get_options()["model_source"] == "Local (.pkl)"
    monkeypatch.setenv("USE_MLFLOW", "true")
    assert predictor.get_options()["model_source"] == "MLflow Registry"
