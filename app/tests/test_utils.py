import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils import top_station_volumes, train_vs_plane_comparison, format_passenger_millions


def test_top_station_volumes():
    df = pd.DataFrame(
        [
            {"station_name": "A", "annual_passengers_millions": 10.0},
            {"station_name": "B", "annual_passengers_millions": 25.0},
            {"station_name": "C", "annual_passengers_millions": 5.0},
        ]
    )

    top = top_station_volumes(df, top_n=2)

    assert len(top) == 2
    assert top.iloc[0]["station_name"] == "B"
    assert top.iloc[1]["station_name"] == "A"


def test_train_vs_plane_comparison():
    df = pd.DataFrame(
        [
            {"Pays": "France", "Emissions_Train_g_km": 10.0, "Emissions_Avion_g_km": 250.0},
            {"Pays": "Allemagne", "Emissions_Train_g_km": 15.0, "Emissions_Avion_g_km": 270.0},
        ]
    )

    compare = train_vs_plane_comparison(df)
    assert list(compare.columns) == ["Pays", "Emissions_Train_g_km", "Emissions_Avion_g_km"]
    assert compare.loc[0, "Pays"] == "France"


def test_format_passenger_millions():
    assert format_passenger_millions(12.345) == "12.3 M"
    assert format_passenger_millions(0.0) == "0.0 M"
