import os
import requests
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models.trajet import Trajet
from schemas.trajet_schema import TrajetCreate, TrajetResponse

from auth.dependencies import get_current_user

router = APIRouter(
    prefix="/trajets",
    tags=["Trajets"]
)

BC_ENABLED = os.getenv("BC_ENABLED", "true").lower() == "true"
BC_BASE_URL = os.getenv("BC_BASE_URL")
BC_ACCESS_TOKEN = os.getenv("BC_ACCESS_TOKEN")
BC_COMPANY_ID = os.getenv("BC_COMPANY_ID")
BC_COMPANIES_PATH = os.getenv("BC_COMPANIES_PATH", "/companies")
BC_RAILTRIPS_PATH = os.getenv("BC_RAILTRIPS_PATH")


def _get_bc_headers() -> dict[str, str]:
    if not BC_ACCESS_TOKEN:
        raise RuntimeError(
            "BC_ACCESS_TOKEN n'est pas configuré. Placez votre token Microsoft Graph dans API/.env."
        )
    return {"Authorization": f"Bearer {BC_ACCESS_TOKEN}"}


def _get_bc_root() -> str:
    if not BC_BASE_URL:
        raise RuntimeError(
            "BC_BASE_URL n'est pas configuré. Définissez BC_BASE_URL dans API/.env."
        )

    return BC_BASE_URL.rstrip("/")


def _fetch_bc_raw(path: str):
    base = _get_bc_root()

    if not path.startswith("/"):
        path = "/" + path

    if base.endswith("/api/v2.0") and path.startswith("/api/"):
        url = f"{base[:-len('/api/v2.0')]}{path}"
    elif base.endswith("/api") and path.startswith("/api/"):
        url = f"{base[:-len('/api')]}{path}"
    else:
        url = f"{base}{path}"

    return requests.get(url, headers=_get_bc_headers())


def _fetch_bc(path: str) -> dict:
    response = _fetch_bc_raw(path)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail={
                "message": "Requête Business Central échouée",
                "url": response.url,
                "body": response.text,
            },
        )

    return response.json()


def _render_bc_path(path: str, company_id: str, company_id_quoted: str) -> str:
    return path.format(company_id=company_id, company_id_quoted=company_id_quoted)


def _fetch_bc_candidates(candidate_paths: list[str]) -> dict:
    errors = []
    for path in candidate_paths:
        if not path:
            continue

        response = _fetch_bc_raw(path)
        if response.status_code == 200:
            return response.json()
        if response.status_code != 404:
            raise HTTPException(
                status_code=response.status_code,
                detail={
                    "message": "Requête Business Central échouée",
                    "url": response.url,
                    "body": response.text,
                },
            )
        errors.append({"path": path, "status": response.status_code, "body": response.text})

    raise HTTPException(
        status_code=404,
        detail={
            "message": "Aucun endpoint Business Central RailTrips trouvé.",
            "tried": errors,
        },
    )


def _get_default_company_id() -> str:
    if BC_COMPANY_ID:
        return BC_COMPANY_ID

    companies = _fetch_bc(BC_COMPANIES_PATH)
    values = companies.get("value") or []
    if not values:
        raise HTTPException(status_code=404, detail="Aucune société Business Central disponible.")

    company_id = values[0].get("id")
    if not company_id:
        raise HTTPException(status_code=404, detail="Impossible de lire l'identifiant de la société Business Central.")

    return company_id


def _format_company_id(company_id: str) -> tuple[str, str]:
    company_id_raw = str(company_id)
    company_id_quoted = company_id_raw
    if not company_id_raw.isdigit():
        escaped = company_id_raw.replace("'", "''")
        company_id_quoted = f"'{escaped}'"
    return company_id_raw, company_id_quoted


def _normalize_bc_trajet(item: dict) -> dict:
    return {
        "year": item.get("year"),
        "origin_country": item.get("originCountry"),
        "origin_station_name": item.get("originStationName"),
        "origin_city": item.get("originCity"),
        "origin_region": item.get("originRegion"),
        "destination_country": item.get("destinationCountry"),
        "destination_station_name": item.get("destinationStationName"),
        "destination_city": item.get("destinationCity"),
        "destination_region": item.get("destinationRegion"),
        "passengers_millions": item.get("passengersMillions"),
        "type": item.get("type"),
        "origin_lat": item.get("originLat"),
        "origin_lon": item.get("originLon"),
        "destination_lat": item.get("destinationLat"),
        "destination_lon": item.get("destinationLon"),
        "distance_km": item.get("distanceKm"),
        "co2_predicted": item.get("co2Predicted"),
        "anomaly_score": item.get("anomalyScore"),
        "prediction_status": item.get("predictionStatus"),
        "source": "BusinessCentral",
    }


def _get_railtrips_candidate_paths(company_id_raw: str, company_id_quoted: str) -> list[str]:
    paths: list[str] = []
    if BC_RAILTRIPS_PATH:
        paths.append(_render_bc_path(BC_RAILTRIPS_PATH, company_id_raw, company_id_quoted))

    common_paths = [
        f"/api/DefaultPublisher/integration/v2.0/companies({company_id_raw})/RailTrips",
        f"/api/DefaultPublisher/integration/v2.0/companies({company_id_quoted})/RailTrips",
        f"/api/DefaultPublisher/integration/v2.0/companies({company_id_raw})/RailTrips?$top=100",
        f"/api/DefaultPublisher/integration/v2.0/companies({company_id_quoted})/RailTrips?$top=100",
        f"/api/DefaultPublisher/integration/v2.0/RailTrips",
        f"/api/DefaultPublisher/integration/v2.0/RailTrips?$top=100",
        f"/companies({company_id_raw})/DefaultPublisher_integration/RailTrips",
        f"/companies({company_id_raw})/DefaultPublisher_integration_RailTrips",
        f"/companies({company_id_raw})/integration/v2.0/RailTrips",
        f"/companies({company_id_raw})/integration_v2.0_RailTrips",
        f"/companies({company_id_raw})/DefaultPublisher/RailTrips",
        f"/companies({company_id_raw})/DefaultPublisher_RailTrips",
        f"/companies({company_id_raw})/integration/RailTrips",
        f"/companies({company_id_raw})/integration_RailTrips",
        f"/companies({company_id_raw})/page/50102",
        f"/companies({company_id_raw})/Page/50102",
        f"/companies({company_id_raw})/page/50102?$top=100",
        f"/companies({company_id_raw})/Page/50102?$top=100",
        f"/companies({company_id_quoted})/DefaultPublisher_integration/RailTrips",
        f"/companies({company_id_quoted})/DefaultPublisher_integration_RailTrips",
        f"/companies({company_id_quoted})/integration/v2.0/RailTrips",
        f"/companies({company_id_quoted})/integration_v2.0_RailTrips",
        f"/companies({company_id_quoted})/DefaultPublisher/RailTrips",
        f"/companies({company_id_quoted})/DefaultPublisher_RailTrips",
        f"/companies({company_id_quoted})/integration/RailTrips",
        f"/companies({company_id_quoted})/integration_RailTrips",
        f"/companies({company_id_quoted})/page/50102",
        f"/companies({company_id_quoted})/Page/50102",
        f"/companies({company_id_quoted})/page/50102?$top=100",
        f"/companies({company_id_quoted})/Page/50102?$top=100",
        "/DefaultPublisher_integration/RailTrips",
        "/DefaultPublisher_integration_RailTrips",
        "/integration/v2.0/RailTrips",
        "/integration_v2.0_RailTrips",
        "/DefaultPublisher/RailTrips",
        "/DefaultPublisher_RailTrips",
        "/integration/RailTrips",
        "/integration_RailTrips",
        "/page/50102",
        "/Page/50102",
    ]

    for path in common_paths:
        if path not in paths:
            paths.append(path)

    return paths


def _get_bc_trajets() -> list[dict]:
    company_id = _get_default_company_id()
    company_id_raw, company_id_quoted = _format_company_id(company_id)

    candidate_paths = _get_railtrips_candidate_paths(company_id_raw, company_id_quoted)

    raw = _fetch_bc_candidates(candidate_paths)
    items = raw.get("value") if isinstance(raw, dict) else raw
    if items is None:
        items = []

    return [_normalize_bc_trajet(item) for item in items]


def _get_local_trajets(
    year: Optional[int],
    service_type: Optional[str],
    origin_region: Optional[str],
    destination_region: Optional[str],
    search: Optional[str],
    limit: int,
) -> list[Trajet]:
    query = SessionLocal = None
    query = get_db()  # type: ignore
    # fallback logic is intentionally not used; local DB route remains unchanged
    return []


@router.get("/filters")
def get_trajet_filters(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Valeurs distinctes disponibles pour alimenter les filtres de l'interface."""
    if BC_ENABLED and BC_BASE_URL and BC_ACCESS_TOKEN:
        trajets = _get_bc_trajets()

        def _distinct(key):
            return sorted({t[key] for t in trajets if t.get(key) is not None})

        return {
            "years": _distinct("year"),
            "service_types": _distinct("type"),
            "origin_regions": _distinct("origin_region"),
            "destination_regions": _distinct("destination_region"),
        }

    def _distinct(column):
        rows = db.query(column).distinct().all()
        return sorted({r[0] for r in rows if r[0] is not None})

    return {
        "years": _distinct(Trajet.year),
        "service_types": _distinct(Trajet.type),
        "origin_regions": _distinct(Trajet.origin_region),
        "destination_regions": _distinct(Trajet.destination_region),
    }


@router.get(
    "/",
    response_model=list[TrajetResponse]
)
def get_trajets(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    year: Optional[int] = None,
    service_type: Optional[str] = None,
    origin_region: Optional[str] = None,
    destination_region: Optional[str] = None,
    search: Optional[str] = Query(default=None, description="Filtre sur le nom des gares (origine ou destination)"),
    limit: int = Query(default=500, ge=1, le=5000),
):
    """Liste des trajets, avec filtres optionnels (année, type de service, régions, recherche gare)."""
    if BC_ENABLED and BC_BASE_URL and BC_ACCESS_TOKEN:
        trajets = _get_bc_trajets()

        if year is not None:
            trajets = [t for t in trajets if t.get("year") == year]
        if service_type:
            trajets = [t for t in trajets if t.get("type") == service_type]
        if origin_region:
            trajets = [t for t in trajets if t.get("origin_region") == origin_region]
        if destination_region:
            trajets = [t for t in trajets if t.get("destination_region") == destination_region]
        if search:
            text = search.lower()
            trajets = [
                t for t in trajets
                if text in (t.get("origin_station_name") or "").lower()
                or text in (t.get("destination_station_name") or "").lower()
            ]
        return trajets[:limit]

    query = db.query(Trajet)

    if year is not None:
        query = query.filter(Trajet.year == year)
    if service_type:
        query = query.filter(Trajet.type == service_type)
    if origin_region:
        query = query.filter(Trajet.origin_region == origin_region)
    if destination_region:
        query = query.filter(Trajet.destination_region == destination_region)
    if search:
        like = f"%{search}%"
        query = query.filter(
            Trajet.origin_station_name.ilike(like)
            | Trajet.destination_station_name.ilike(like)
        )

    return query.limit(limit).all()


@router.post("/")
def create_trajet(
    trajet: TrajetCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    new_trajet = Trajet(
        year=trajet.year,
        origin_station_name=trajet.origin_station_name,
        destination_station_name=trajet.destination_station_name,
        origin_city=trajet.origin_city,
        destination_city=trajet.destination_city,
        origin_region=trajet.origin_region,
        destination_region=trajet.destination_region,
        passengers_millions=trajet.passengers_millions,
        type=trajet.type,
        source=trajet.source
    )

    db.add(new_trajet)
    db.commit()

    return {
        "message": "Trajet créé"
    }
