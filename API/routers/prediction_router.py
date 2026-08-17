import os

from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import get_current_user
from schemas.prediction_schema import PredictionRequest, PredictionResponse
from ml.predictor import predict_co2, get_options

router = APIRouter(
    prefix="/predict",
    tags=["Prédiction CO2"],
)


@router.get("/options")
def prediction_options(current_user: str = Depends(get_current_user)):
    """Listes de valeurs pour le formulaire de prédiction + métriques du modèle."""
    return get_options()


@router.post("/co2", response_model=PredictionResponse)
def predict(
    request: PredictionRequest,
    current_user: str = Depends(get_current_user),
):
    """Prédit l'empreinte CO₂ ferroviaire (g/km) via le modèle XGBoost et la compare voiture/avion."""
    try:
        if os.getenv("E2E_TEST_MODE") == "1":
            return {
                "train_g_km": 20.0,
                "car_g_km": 120.0,
                "plane_g_km": 180.0,
                "co2_saved_vs_car_g_km": 100.0,
                "co2_saved_vs_plane_g_km": 160.0,
                "distance_km": request.distance_km,
                "total_train_kg": 8.6 if request.distance_km else None,
                "total_car_kg": 51.6 if request.distance_km else None,
                "total_plane_kg": 77.4 if request.distance_km else None,
            }

        return predict_co2(request.model_dump())

    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=400,
            detail=f"Échec de la prédiction : {exc}",
        )