from typing import Optional
from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    origin_station: str
    destination_station: str
    service_type: str
    year: int = 2024
    passengers_millions: float = 1.0
    heure: int = Field(default=9, ge=0, le=23)
    jour_semaine: str = "Monday"
    mois: int = Field(default=6, ge=1, le=12)
    est_jour_ferie: int = Field(default=0, ge=0, le=1)
    distance_km: Optional[float] = Field(default=None, gt=0)


class PredictionResponse(BaseModel):
    train_g_km: float
    car_g_km: float
    plane_g_km: float
    co2_saved_vs_car_g_km: float
    co2_saved_vs_plane_g_km: float
    flow_type: str
    origin_country_iso: str
    distance_km: Optional[float] = None
    total_train_kg: Optional[float] = None
    total_car_kg: Optional[float] = None
    total_plane_kg: Optional[float] = None
