import csv
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(
    prefix="/stats",
    tags=["Stats"]
)


def _load_station_volumes(country: str) -> List[Dict[str, Any]]:
    import os
    if os.path.exists("/data"):
        print("data ok")
    file_path = Path(f"/data/frequentation_gares/frequentation_gares_{country}.csv")
    if not file_path.exists():
        raise FileNotFoundError(f"Aucun fichier de fréquentation disponible pour le pays '{country}'")

    stations = []
    with file_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                value = float(row.get("annual_passengers_millions", "0").replace(",", "."))
            except ValueError:
                value = 0.0
            stations.append({
                "station_name": row.get("station_name", ""),
                "city": row.get("city", ""),
                "region": row.get("region", ""),
                "annual_passengers_millions": value,
                "type": row.get("type", ""),
            })

    stations.sort(key=lambda item: item["annual_passengers_millions"], reverse=True)
    return stations


def _load_co2_comparison() -> List[Dict[str, Any]]:
    file_path = Path(f"/data/co2_comparaison_europe.csv")
    if not file_path.exists():
        raise FileNotFoundError("Le fichier de comparaison CO2 n'a pas été trouvé")

    comparisons = []
    with file_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            try:
                train_value = float(row.get("Emissions_Train_g_km", "0").replace(",", "."))
            except ValueError:
                train_value = 0.0
            try:
                plane_value = float(row.get("Emissions_Avion_g_km", "0").replace(",", "."))
            except ValueError:
                plane_value = 0.0
            comparisons.append({
                "Pays": row.get("Pays", ""),
                "Emissions_Train_g_km": train_value,
                "Emissions_Avion_g_km": plane_value,
                "Savings_g_km": plane_value - train_value,
            })

    comparisons.sort(key=lambda item: item["Savings_g_km"], reverse=True)
    return comparisons


@router.get("/volumes")
def volumes(country: str = Query("france", description="Nom du pays pour le fichier de fréquentation")):
    try:
        stations = _load_station_volumes(country)
        comparisons = _load_co2_comparison()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur lors du chargement des données de statistiques: {exc}") from exc

    top_stations = stations[:10]
    top_country = comparisons[0] if comparisons else None

    return {
        "country": country,
        "top_stations": top_stations,
        "train_vs_plane_comparison": comparisons[:12],
        "top_train_vs_plane_saving": top_country,
    }