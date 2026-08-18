from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.trajet import Trajet
from auth.dependencies import get_current_user

router = APIRouter(
    prefix="/stats",
    tags=["Statistiques"],
)


# Mots-clés identifiant un service de nuit (trains de nuit européens).
# NB : le jeu de données principal (od_flows) ne contient que des services de jour ;
# cette classification reflètera automatiquement les services de nuit s'ils sont ajoutés.
_NIGHT_KEYWORDS = ("nuit", "night", "notte", "nightjet", "euronight", "nacht", "noche")


def _classify_period(service_type: str) -> str:
    s = (service_type or "").lower()
    return "Nuit" if any(k in s for k in _NIGHT_KEYWORDS) else "Jour"


def _round_map(rows):
    """Transforme [(clé, somme), ...] en dict {clé: somme arrondie}, ordonné décroissant."""
    return {
        (k if k is not None else "N/A"): round(float(v or 0), 2)
        for k, v in sorted(rows, key=lambda r: float(r[1] or 0), reverse=True)
    }


@router.get("/kpi")
def kpi(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Indicateurs clés agrégés depuis la table des trajets :
    volumes totaux, répartition par type de service, par année et par région d'origine,
    et principaux axes (origine → destination).
    """
    total_passengers = db.query(func.sum(Trajet.passengers_millions)).scalar() or 0
    nb_routes = db.query(func.count()).select_from(Trajet).scalar() or 0

    years = [y[0] for y in db.query(Trajet.year).distinct().all() if y[0] is not None]

    service_type_rows = (
        db.query(Trajet.type, func.sum(Trajet.passengers_millions))
        .group_by(Trajet.type).all()
    )
    by_service_type = _round_map(service_type_rows)

    # Répartition jour / nuit (dérivée du type de service)
    by_period = {"Jour": 0.0, "Nuit": 0.0}
    for service_type, total in service_type_rows:
        by_period[_classify_period(service_type)] += float(total or 0)
    by_period = {k: round(v, 2) for k, v in by_period.items()}

    by_year = {
        int(y): round(float(v or 0), 2)
        for y, v in sorted(
            db.query(Trajet.year, func.sum(Trajet.passengers_millions))
            .group_by(Trajet.year).all(),
            key=lambda r: r[0],
        )
    }

    by_region = dict(
        list(
            _round_map(
                db.query(Trajet.origin_region, func.sum(Trajet.passengers_millions))
                .group_by(Trajet.origin_region).all()
            ).items()
        )[:10]
    )

    top_routes = [
        {
            "origin": o,
            "destination": d,
            "passengers_millions": round(float(v or 0), 2),
        }
        for o, d, v in db.query(
            Trajet.origin_station_name,
            Trajet.destination_station_name,
            func.sum(Trajet.passengers_millions),
        )
        .group_by(Trajet.origin_station_name, Trajet.destination_station_name)
        .order_by(func.sum(Trajet.passengers_millions).desc())
        .limit(10)
        .all()
    ]

    return {
        "total_passengers_millions": round(float(total_passengers), 2),
        "nb_routes": int(nb_routes),
        "nb_service_types": len(by_service_type),
        "years_covered": sorted(int(y) for y in years),
        "by_service_type": by_service_type,
        "by_period": by_period,
        "by_year": by_year,
        "by_origin_region_top10": by_region,
        "top_routes": top_routes,
    }
