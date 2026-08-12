from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from auth.dependencies import get_current_user
from observability import request_summary

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
)


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """
    État de santé du service (public). Vérifie la connectivité à la base de données.
    Renvoie 200 avec status "ok" ou "degraded" selon l'accès à la base.
    """
    database_up = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_up = False

    return {
        "status": "ok" if database_up else "degraded",
        "api": "up",
        "database": "up" if database_up else "down",
    }


@router.get("/summary")
def monitoring_summary(current_user: str = Depends(get_current_user)):
    """
    Synthèse du trafic et des incidents détectés (réponses 4xx/5xx),
    calculée à partir des compteurs Prometheus en mémoire.
    """
    return request_summary()
