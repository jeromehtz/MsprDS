import os

import requests
from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import get_current_user

router = APIRouter(
    prefix="/businesscentral",
    tags=["Business Central"],
)

BC_BASE_URL = os.getenv("BC_BASE_URL")
BC_ACCESS_TOKEN = os.getenv("BC_ACCESS_TOKEN")
BC_COMPANIES_PATH = os.getenv("BC_COMPANIES_PATH", "/companies")
BC_RAILTRIPS_PATH = os.getenv("BC_RAILTRIPS_PATH")


def _get_bc_headers() -> dict[str, str]:
    if not BC_ACCESS_TOKEN:
        raise RuntimeError(
            "BC_ACCESS_TOKEN is not configured. Place your Microsoft Graph access token in API/.env."
        )
    return {"Authorization": f"Bearer {BC_ACCESS_TOKEN}"}


def _fetch_bc_raw(path: str):
    if not BC_BASE_URL:
        raise RuntimeError(
            "BC_BASE_URL is not configured. Set BC_BASE_URL in API/.env."
        )

    if not path.startswith("/"):
        path = "/" + path

    url = f"{BC_BASE_URL}{path}"
    return requests.get(url, headers=_get_bc_headers())


def _fetch_bc(path: str) -> dict:
    response = _fetch_bc_raw(path)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail={
                "message": "Business Central request failed",
                "url": response.url,
                "body": response.text,
            },
        )

    return response.json()


def _format_company_id(company_id: str) -> tuple[str, str]:
    quoted = company_id
    if isinstance(company_id, str) and not company_id.isdigit():
        escaped = company_id.replace("'", "''")
        quoted = f"'{escaped}'"
    return company_id, quoted


def _get_default_company_id() -> str:
    companies = _fetch_bc(BC_COMPANIES_PATH)
    values = companies.get("value") or []
    if not values:
        raise HTTPException(status_code=404, detail="Aucune société Business Central disponible.")

    company_id = values[0].get("id")
    if not company_id:
        raise HTTPException(status_code=404, detail="Impossible de lire l'identifiant de société Business Central.")

    return company_id


def _render_bc_path(path: str, company_id: str, company_id_quoted: str) -> str:
    return path.format(company_id=company_id, company_id_quoted=company_id_quoted)


def _get_railtrips_candidate_paths(company_id_raw: str, company_id_quoted: str) -> list[str]:
    paths: list[str] = []
    if BC_RAILTRIPS_PATH:
        paths.append(_render_bc_path(BC_RAILTRIPS_PATH, company_id_raw, company_id_quoted))

    common_paths = [
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


def _fetch_bc_candidates(candidate_paths: list[str]):
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
                    "message": "Business Central request failed",
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


@router.get("/companies")
def get_companies(current_user: str = Depends(get_current_user)):
    """Récupère la liste des sociétés depuis Business Central."""
    return _fetch_bc(BC_COMPANIES_PATH)


@router.get("/railtrips")
def get_railtrips(company_id: str | None = None, current_user: str = Depends(get_current_user)):
    """Récupère les RailTrips depuis Business Central.

    Si `company_id` n'est pas fourni, la première société disponible est utilisée.
    """
    if not company_id:
        company_id = _get_default_company_id()

    company_id_raw, company_id_quoted = _format_company_id(company_id)
    candidate_paths = _get_railtrips_candidate_paths(company_id_raw, company_id_quoted)
    return _fetch_bc_candidates(candidate_paths)
