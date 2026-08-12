"""
Enregistre le modèle XGBoost CO₂ dans MLflow (tracking + Model Registry).

Lit le bundle `modele_XGB_co2_ULTIMATE.pkl` (modèle + métriques + hyper-paramètres
+ métadonnées de features), puis :
  - journalise les hyper-paramètres et les métriques de test (MAE / RMSE / R²),
  - logge le modèle XGBoost (flavor mlflow.xgboost),
  - logge les métadonnées de features (feature_names, encodage catégoriel),
  - enregistre le modèle sous le nom `co2-xgboost` dans le Model Registry.

Usage :
    MLFLOW_TRACKING_URI=http://localhost:5000 python model/register_mlflow.py

Le Model Registry nécessite un backend store base de données (sqlite/postgres),
ce que fournit le service `mlflow` du docker-compose.
"""

import os

# Évite le bloc d'avertissement GitPython quand git n'est pas installé (conteneur).
os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

import pickle
from pathlib import Path

import mlflow
import mlflow.xgboost

ROOT = Path(__file__).resolve().parent
MODEL_PKL = Path(os.getenv("MODEL_PATH", ROOT / "modele_XGB_co2_ULTIMATE.pkl"))
REGISTERED_NAME = os.getenv("MLFLOW_REGISTERED_NAME", "co2-xgboost")
EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "co2-emissions")


def main():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(EXPERIMENT)

    with open(MODEL_PKL, "rb") as f:
        bundle = pickle.load(f)

    model = bundle["model"]
    metrics = {k: float(v) for k, v in bundle["test_metrics"].items() if k != "model"}
    params = bundle.get("best_params", {})

    with mlflow.start_run(run_name="xgboost-co2") as run:
        if params:
            mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.log_dict(
            {
                "feature_names": bundle["feature_names"],
                "categorical_features": bundle["categorical_features"],
                "target": bundle["target"],
                "encoding": bundle.get("encoding"),
            },
            "feature_metadata.json",
        )
        mlflow.log_dict(bundle["category_mappings"], "category_mappings.json")

        info = mlflow.xgboost.log_model(
            xgb_model=model,
            artifact_path="model",
            registered_model_name=REGISTERED_NAME,
        )

        print(f"✅ Modèle enregistré dans MLflow ({tracking_uri})")
        print(f"   run_id    : {run.info.run_id}")
        print(f"   model_uri : {info.model_uri}")
        print(f"   registry  : models:/{REGISTERED_NAME}/latest")
        print(f"   metrics   : {metrics}")


if __name__ == "__main__":
    main()
