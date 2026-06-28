from pathlib import Path
import pickle
import importlib
import joblib
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

router = APIRouter(
    prefix="/model",
    tags=["Model"]
)

MODEL_PATH = Path(__file__).resolve().parent.parent / "modèle" / "modele_RF_co2_ULTIMATE.pkl"


def _load_model() -> Any:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Le modèle n'a pas été trouvé à l'emplacement : {MODEL_PATH}")
    # Try standard pickle load first
    with MODEL_PATH.open("rb") as handle:
        try:
            return pickle.load(handle)
        except ModuleNotFoundError:
            pass
        except Exception:
            # fall through to joblib attempt
            pass

    # Try a compatibility unpickler that can resolve known sklearn classes
    class CompatUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            try:
                return super().find_class(module, name)
            except (ModuleNotFoundError, AttributeError):
                # Common sklearn mapping
                if name in ("RandomForestRegressor", "RandomForestClassifier"):
                    mod = importlib.import_module("sklearn.ensemble")
                    return getattr(mod, name)
                if name in ("DecisionTreeRegressor", "DecisionTreeClassifier"):
                    mod = importlib.import_module("sklearn.tree")
                    return getattr(mod, name)
                # Try importing the module directly
                try:
                    mod = importlib.import_module(module)
                    return getattr(mod, name)
                except Exception:
                    # fallback: try sklearn.ensemble
                    try:
                        mod = importlib.import_module("sklearn.ensemble")
                        return getattr(mod, name)
                    except Exception:
                        raise

    with MODEL_PATH.open("rb") as handle:
        try:
            return CompatUnpickler(handle).load()
        except Exception:
            pass

    # Final fallback: joblib.load (commonly used to persist sklearn models)
    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:
        raise RuntimeError(f"Impossible de charger le modèle: {exc}") from exc


MODEL = _load_model()

EXPECTED_FEATURES: Optional[int] = None
FEATURE_NAMES: Optional[List[str]] = None

if hasattr(MODEL, "n_features_in_"):
    try:
        EXPECTED_FEATURES = int(getattr(MODEL, "n_features_in_"))
    except Exception:
        EXPECTED_FEATURES = None

if hasattr(MODEL, "feature_names_in_"):
    try:
        FEATURE_NAMES = list(getattr(MODEL, "feature_names_in_"))
    except Exception:
        FEATURE_NAMES = None

# Build useful OpenAPI examples using detected model shape
_example_len = EXPECTED_FEATURES or 29
EXAMPLE_LIST = [
    120.0, 60.0, 1.0, 0.5, 0.3, 150.0, 30.0, 2.0, 0.8, 1.0,
    0.0, 250.0, 1.0, 0.2, 80.0, 0.1, 0.0, 1.0, 0.0, 45.0,
    0.6, 0.05, 0.0, 7.0, 0.0, 0.0, 0.0, 0.0, 0.0
]
if len(EXAMPLE_LIST) != _example_len:
    EXAMPLE_LIST = [0.0] * _example_len
if FEATURE_NAMES:
    # create a dict with the first N feature names assigned realistic sample values
    EXAMPLE_DICT = {
        name: EXAMPLE_LIST[i] if i < len(EXAMPLE_LIST) else 0.0
        for i, name in enumerate(FEATURE_NAMES)
    }
else:
    # fallback named keys
    EXAMPLE_DICT = {f"f{i+1}": EXAMPLE_LIST[i] if i < len(EXAMPLE_LIST) else 0.0 for i in range(_example_len)}

EXAMPLES = {
    "list": {"summary": "Flat list of sample features", "value": {"features": EXAMPLE_LIST}},
    "dict": {"summary": "Named sample features", "value": {"features": EXAMPLE_DICT}},
}


class PredictRequest(BaseModel):
    features: Optional[Union[List[Union[float, int, Dict[str, Any]]], Dict[str, Union[float, int]]]] = None
    data: Optional[Union[List[Union[float, int, Dict[str, Any]]], Dict[str, Union[float, int]]]] = None


def _normalize_features(
    raw: Union[List, Tuple, Dict],
    expected_len: Optional[int] = EXPECTED_FEATURES,
    feature_names: Optional[List[str]] = FEATURE_NAMES,
) -> List[List[float]]:
    # Accept dict (single row), list of numbers, list of dicts, or single list
    if raw is None:
        raise ValueError("Aucun jeu de caractéristiques fourni")

    # If dict: produce one-row list using feature_names order when available
    if isinstance(raw, dict):
        if feature_names:
            row = [raw.get(k) for k in feature_names]
        else:
            row = list(raw.values())
        rows = [row]
    elif isinstance(raw, (list, tuple)) and raw and isinstance(raw[0], dict):
        # list of dicts
        if feature_names:
            rows = [[item.get(k) for k in feature_names] for item in raw]
        else:
            rows = [[v for v in item.values()] for item in raw]
    elif isinstance(raw, (list, tuple)) and raw and not isinstance(raw[0], (list, tuple)):
        # flat list -> single row
        rows = [list(raw)]
    else:
        # assume already list-of-lists
        rows = [list(r) for r in raw]

    # Convert to floats and validate with precise errors
    converted: List[List[float]] = []
    for row_idx, r in enumerate(rows):
        conv: List[float] = []
        for col_idx, x in enumerate(r):
            if isinstance(x, dict):
                key_name = None
                if feature_names and col_idx < len(feature_names):
                    key_name = feature_names[col_idx]
                if key_name:
                    raise ValueError(
                        f"Caractéristique non scalaire pour l'index {col_idx} (nom '{key_name}') dans la ligne {row_idx}: reçu un objet/dict, attendu un nombre"
                    )
                else:
                    raise ValueError(
                        f"Caractéristique non scalaire pour l'index {col_idx} dans la ligne {row_idx}: reçu un objet/dict, attendu un nombre"
                    )
            try:
                conv.append(float(x))
            except Exception as exc:
                raise ValueError(
                    f"Impossible de convertir la caractéristique index={col_idx} value={x!r} en float (ligne {row_idx}): {exc}"
                ) from exc
        converted.append(conv)

    if expected_len is not None:
        for r_idx, r in enumerate(converted):
            if len(r) != expected_len:
                raise ValueError(f"Le modèle attend {expected_len} caractéristiques par ligne, mais la ligne {r_idx} en contient {len(r)}")

    return converted


@router.get("/")
def home():
    return {"message": "Model ready"}


@router.get("/metadata")
def metadata():
    """Return model metadata useful for building prediction payloads."""
    # determine estimator type if artifact is a container
    estimator_type = None
    if isinstance(MODEL, dict):
        for key in ("model", "estimator", "pipeline", "est"):
            if key in MODEL and hasattr(MODEL[key], "predict"):
                estimator_type = type(MODEL[key]).__name__
                break
        else:
            for v in MODEL.values():
                if hasattr(v, "predict"):
                    estimator_type = type(v).__name__
                    break
    else:
        estimator_type = type(MODEL).__name__

    return {
        "model_path": str(MODEL_PATH),
        "loaded": MODEL is not None,
        "estimator_type": estimator_type,
        "n_features_in": EXPECTED_FEATURES,
        "feature_names_in": FEATURE_NAMES,
    }


@router.post("/predict")
def predict(req: PredictRequest = Body(..., example=EXAMPLES["list"]["value"], examples=EXAMPLES)):
    try:
        raw = req.features if req.features is not None else req.data
        if raw is None:
            raise ValueError("Le corps de la requête doit contenir 'features' ou 'data'.")

        features = _normalize_features(raw, expected_len=EXPECTED_FEATURES, feature_names=FEATURE_NAMES)

        # The persisted artifact may be the estimator itself, or a dict/container
        model_obj = MODEL
        if isinstance(MODEL, dict):
            # try common keys
            for key in ("model", "estimator", "pipeline", "est"):
                if key in MODEL and hasattr(MODEL[key], "predict"):
                    model_obj = MODEL[key]
                    break
            else:
                # try to find any value with predict
                for v in MODEL.values():
                    if hasattr(v, "predict"):
                        model_obj = v
                        break

        if not hasattr(model_obj, "predict"):
            raise ValueError("L'objet chargé ne dispose pas d'une méthode 'predict'.")

        prediction = model_obj.predict(features)
        prediction_value = prediction[0]

        if hasattr(prediction_value, "tolist"):
            prediction_value = prediction_value.tolist()

        return {"result": prediction_value}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc