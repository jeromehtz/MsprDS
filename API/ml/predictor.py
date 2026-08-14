"""
Service d'inférence CO₂ basé sur le modèle XGBoost entraîné (model/modele_XGB_co2_ULTIMATE.pkl).

Le modèle prédit `emissions_train_g_km` à partir de 29 caractéristiques (14 numériques
+ 15 catégorielles). Le fichier .pkl embarque, en plus du modèle :
  - feature_names        : ordre exact des colonnes attendues
  - categorical_features : colonnes à encoder en `category`
  - category_mappings    : modalités connues par colonne (pour reproduire l'encodage)
  - test_metrics         : MAE / RMSE / R² sur le jeu de test

Pour rester utilisable, l'utilisateur ne fournit que les champs significatifs
(gares, type de service, contexte temporel). Les autres caractéristiques (ville,
région, pays, facteur voiture, météo, coordonnées…) sont déduites de référentiels
(`od_flows_enriched.csv`, `co2_comparaison_europe.csv`) ou complétées par des valeurs
par défaut raisonnables — ces dernières ont un impact marginal, la cible étant très
largement déterminée par le pays / l'itinéraire (R² ≈ 0.999).
"""

import os
import pickle
from functools import lru_cache
from pathlib import Path
import xgboost as xgb
import re
import pandas as pd

# Racine du dépôt : API/ml/predictor.py -> parents[2]
ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.getenv("MODEL_PATH", ROOT / "model" / "modele_XGB_co2_ULTIMATE.pkl"))
OD_FLOWS_PATH = Path(os.getenv("OD_FLOWS_PATH", ROOT / "data" / "etl_output" / "od_flows_enriched.csv"))
CO2_REF_PATH = Path(os.getenv("CO2_REF_PATH", ROOT / "data" / "co2_comparaison_europe.csv"))

# Facteurs d'émission voiture / avion (g CO₂/km) par pays, issus de co2_comparaison_europe.csv.
# Correspondance code ISO -> nom de pays utilisé dans le CSV.
_ISO_TO_PAYS = {"FR": "France", "CH": "Suisse", "PT": "Portugal", "DE": "Allemagne", "IT": "Italie"}

# Valeurs par défaut des caractéristiques non saisies par l'utilisateur.
_NUMERIC_DEFAULTS = {
    "passengers_millions": 1.0,
    "frequentation_ville_depart_millions": 5.0,
    "frequentation_ville_arrivee_millions": 5.0,
    "est_jour_ferie": 0,
    "lat_origine": 0.0,
    "lon_origine": 0.0,
    "lat_destination": 0.0,
    "lon_destination": 0.0,
    "temperature_moyenne": 15.0,
    "pluie_mm": 0.0,
}


@lru_cache(maxsize=1)
def _bundle():
    """Charge et met en cache le bundle du modèle (modèle + métadonnées)."""
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def _use_mlflow() -> bool:
    return os.getenv("USE_MLFLOW", "").lower() in ("1", "true", "yes")


@lru_cache(maxsize=1)
def _model():
    """
    Renvoie le modèle XGBoost utilisé pour l'inférence.

    Si `USE_MLFLOW=true`, le modèle est chargé depuis le Model Registry MLflow
    (`MLFLOW_MODEL_URI`, par défaut `models:/co2-xgboost/latest`). En cas d'échec
    (serveur indisponible, modèle non enregistré…), repli automatique sur le .pkl local.
    Les métadonnées (features, encodage) proviennent toujours du bundle local.
    """
    if _use_mlflow():
        model_uri = os.getenv("MLFLOW_MODEL_URI", "models:/co2-xgboost/latest")
        try:
            import mlflow.xgboost  # import paresseux : MLflow optionnel

            tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)
            model = mlflow.xgboost.load_model(model_uri)
            print(f"[predictor] Modèle chargé depuis MLflow : {model_uri}")
            return model
        except Exception as exc:  # repli robuste
            print(f"[predictor] MLflow indisponible ({exc}); repli sur le modèle local .pkl")

    return _bundle()["model"]


@lru_cache(maxsize=1)
def _station_index():
    """
    Construit, depuis od_flows_enriched.csv, un index gare -> (ville, région, pays ISO),
    ainsi que les facteurs voiture/avion par pays.
    Retourne (stations: dict, car_by_iso: dict, plane_by_iso: dict).
    """
    stations = {}
    car_by_iso = {}
    if OD_FLOWS_PATH.exists():
        df = pd.read_csv(OD_FLOWS_PATH, sep=";")
        for side in ("origin", "destination"):
            cols = df[[f"{side}_station", f"{side}_city", f"{side}_region", f"{side}_country_iso"]].dropna()
            for st, city, region, iso in cols.itertuples(index=False):
                stations.setdefault(st, {"city": city, "region": region, "country_iso": iso})
        car = df.dropna(subset=["emissions_car_g_km"]).groupby("origin_country_iso")["emissions_car_g_km"].first()
        car_by_iso = {k: float(v) for k, v in car.items()}

    plane_by_iso = {}
    if CO2_REF_PATH.exists():
        ref = pd.read_csv(CO2_REF_PATH, sep=";")
        by_pays = ref.set_index("Pays")
        for iso, pays in _ISO_TO_PAYS.items():
            if pays in by_pays.index:
                plane_by_iso[iso] = float(by_pays.loc[pays, "Emissions_Avion_g_km"])
                car_by_iso.setdefault(iso, float(by_pays.loc[pays, "Emissions_Voiture_g_km"]))

    return stations, car_by_iso, plane_by_iso


def _car_factor(iso: str) -> float:
    _, car_by_iso, _ = _station_index()
    return car_by_iso.get(iso, 190.0)  # défaut Europe si pays inconnu


def _plane_factor(iso: str) -> float:
    _, _, plane_by_iso = _station_index()
    return plane_by_iso.get(iso, 250.0)  # défaut Europe si pays inconnu


def _safe_category(value, categories, fallback=None):
    categories = list(categories)

    # Valeur valide
    if value in categories:
        return value

    # Si aucune catégorie n'est disponible
    if not categories:
        return None

    # Le fallback doit lui-même être valide
    if fallback not in categories:
        fallback = categories[0]

    print(
        f"⚠️ Catégorie XGBoost inconnue : "
        f"{value!r}, remplacée par {fallback!r}"
    )

    return fallback


def get_options() -> dict:
    """Valeurs proposables à l'utilisateur (listes déroulantes) + métriques du modèle."""
    b = _bundle()
    cm = b["category_mappings"]
    return {
        "stations": sorted(cm["origin_station"]),
        "service_types": sorted(cm["service_type"]),
        "jours_semaine": cm["jour_semaine"],
        "pays_iso": sorted(set(cm["origin_country_iso"])),
        "target": b["target"],
        "metrics": {k: float(v) for k, v in b["test_metrics"].items() if k != "model"},
        "model_name": b["test_metrics"].get("model", "XGBoost"),
        "model_source": "MLflow Registry" if _use_mlflow() else "Local (.pkl)",
    }


def _resolve_station(station: str, iso_default: str = "FR") -> dict:
    stations, _, _ = _station_index()
    info = stations.get(station)
    if info:
        return info
    # Gare inconnue du référentiel : on reste cohérent avec des valeurs neutres.
    return {"city": station, "region": "", "country_iso": iso_default}


def predict_co2(payload: dict) -> dict:
    """
    Prédit l'empreinte CO₂ ferroviaire (g/km) pour un trajet et la compare voiture/avion.

    `payload` (champs saisis par l'utilisateur, les autres sont déduits/complétés) :
        origin_station, destination_station, service_type, year,
        passengers_millions, heure, jour_semaine, mois, est_jour_ferie,
        distance_km (optionnel, pour calculer un total par mode)
    """
    b = _bundle()
    model = _model()
    feats = b["feature_names"]
    cats = b["categorical_features"]
    cm = b["category_mappings"]

    o = _resolve_station(payload["origin_station"])
    d = _resolve_station(payload["destination_station"])
    o_iso, d_iso = o["country_iso"], d["country_iso"]
    flow_type = "domestic" if o_iso == d_iso else "cross_border"
    emissions_car = _car_factor(o_iso)

    # Construction de la ligne de features dans l'ordre attendu par le modèle.
    row = {
        "year": int(payload.get("year", 2024)),
        "origin_station": payload["origin_station"],
        "destination_station": payload["destination_station"],
        "origin_city": o["city"],
        "destination_city": d["city"],
        "origin_region": o["region"],
        "destination_region": d["region"],
        "passengers_millions": float(payload.get("passengers_millions", 1.0)),
        "service_type": payload["service_type"],
        "flow_type": flow_type,
        "origin_country_iso": o_iso,
        "destination_country_iso": d_iso,
        "emissions_car_g_km": emissions_car,
        "origin_city_hierarchy": cm["origin_city_hierarchy"][0],
        "destination_city_hierarchy": cm["destination_city_hierarchy"][0],
        "origin_city_type": cm["origin_city_type"][0],
        "destination_city_type": cm["destination_city_type"][0],
        "frequentation_ville_depart_millions": _NUMERIC_DEFAULTS["frequentation_ville_depart_millions"],
        "frequentation_ville_arrivee_millions": _NUMERIC_DEFAULTS["frequentation_ville_arrivee_millions"],
        "heure": int(payload.get("heure", 9)),
        "jour_semaine": payload.get("jour_semaine", cm["jour_semaine"][0]),
        "mois": int(payload.get("mois", 6)),
        "est_jour_ferie": int(payload.get("est_jour_ferie", 0)),
        "lat_origine": _NUMERIC_DEFAULTS["lat_origine"],
        "lon_origine": _NUMERIC_DEFAULTS["lon_origine"],
        "lat_destination": _NUMERIC_DEFAULTS["lat_destination"],
        "lon_destination": _NUMERIC_DEFAULTS["lon_destination"],
        "temperature_moyenne": _NUMERIC_DEFAULTS["temperature_moyenne"],
        "pluie_mm": _NUMERIC_DEFAULTS["pluie_mm"],
    }

    # Sécurise toutes les colonnes catégorielles vis-à-vis des catégories réellement
    # connues du modèle entraîné (cf. _safe_category) avant de construire le DataFrame.

    for col in cats:
        if col in row:
            original_value = row[col]

            row[col] = _safe_category(
                original_value,
                cm[col],
                fallback=cm[col][0] if cm[col] else None,
            )

            if original_value != row[col]:
                print(
                    f"⚠️ Catégorie remplacée : "
                    f"{col} = {original_value!r} → {row[col]!r}"
                )


    # On construit X seulement après avoir corrigé les catégories
    X = pd.DataFrame([row])[feats]


    # Vérification finale avant XGBoost
    for col in cats:
        value = X.iloc[0][col]

        if value not in cm[col]:
            print(
                f"❌ CATÉGORIE ENCORE INVALIDE : "
                f"col={col!r}, value={value!r}"
            )
        else:
            print(
                f"✅ Catégorie valide : "
                f"col={col!r}, value={value!r}"
            )


    for col in cats:
        X[col] = pd.Categorical(
            X[col],
            categories=cm[col]
        )

    train_g_km = float(model.predict(X)[0])

    car_g_km = float(emissions_car)
    plane_g_km = _plane_factor(o_iso)

    result = {
        "train_g_km": round(train_g_km, 2),
        "car_g_km": round(car_g_km, 2),
        "plane_g_km": round(plane_g_km, 2),
        "co2_saved_vs_car_g_km": round(car_g_km - train_g_km, 2),
        "co2_saved_vs_plane_g_km": round(plane_g_km - train_g_km, 2),
        "flow_type": flow_type,
        "origin_country_iso": o_iso,
    }

    distance_km = payload.get("distance_km")
    if distance_km:
        distance_km = float(distance_km)
        # Totaux du trajet en kg (g/km × km / 1000)
        result["distance_km"] = distance_km
        result["total_train_kg"] = round(train_g_km * distance_km / 1000, 2)
        result["total_car_kg"] = round(car_g_km * distance_km / 1000, 2)
        result["total_plane_kg"] = round(plane_g_km * distance_km / 1000, 2)

    return result