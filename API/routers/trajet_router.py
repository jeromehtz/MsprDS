from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from database import get_db

from models.trajet import Trajet

from schemas.trajet_schema import (
    TrajetCreate,
    TrajetResponse
)

from auth.dependencies import get_current_user

router = APIRouter(
    prefix="/trajets",
    tags=["Trajets"]
)


@router.get(
    "/",
    response_model=list[TrajetResponse]
)
def get_trajets(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    trajets = db.query(Trajet).all()

    return trajets


@router.post("/")
def create_trajet(
    trajet: TrajetCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    new_trajet = Trajet(
        departure_city=trajet.departure_city,
        arrival_city=trajet.arrival_city,
        duration=trajet.duration
    )

    db.add(new_trajet)

    db.commit()

    return {
        "message": "Trajet créé"
    }