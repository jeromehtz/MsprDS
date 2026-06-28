from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.trajet import Trajet
from schemas.trajet_schema import TrajetCreate, TrajetResponse

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
    print(db.query(Trajet).count())
    return trajets


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
