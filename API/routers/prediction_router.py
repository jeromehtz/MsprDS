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
        return predict_co2(request.model_dump())
    except Exception as exc:  # pragma: no cover - garde-fou d'inférence
        raise HTTPException(status_code=400, detail=f"Échec de la prédiction : {exc}")
