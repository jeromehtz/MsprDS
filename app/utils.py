from pathlib import Path
import pandas as pd
from typing import Iterable


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    candidates = [current.parent, *current.parents, Path.cwd()]
    for parent in candidates:
        if (parent / "data" / "co2_comparaison_europe.csv").exists():
            return parent
    for parent in candidates:
        if (parent / "data" / "frequentation_gares" / "frequentation_gares_france.csv").exists():
            return parent
    return current.parent.parent


def load_co2_comparison() -> pd.DataFrame:
    csv_path = get_repo_root() / "data" / "co2_comparaison_europe.csv"
    return pd.read_csv(csv_path, sep=";", encoding="utf-8")


def load_station_frequencies(country: str = "france") -> pd.DataFrame:
    csv_path = get_repo_root() / "data" / "frequentation_gares" / f"frequentation_gares_{country}.csv"
    return pd.read_csv(csv_path, sep=",", encoding="utf-8")


def top_station_volumes(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if "annual_passengers_millions" not in df.columns:
        raise ValueError("DataFrame must contain annual_passengers_millions")
    return (
        df.sort_values(by="annual_passengers_millions", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def train_vs_plane_comparison(df: pd.DataFrame) -> pd.DataFrame:
    expected = {"Pays", "Emissions_Train_g_km", "Emissions_Avion_g_km"}
    if not expected.issubset(df.columns):
        raise ValueError("DataFrame must contain train and plane emission columns")
    return df[["Pays", "Emissions_Train_g_km", "Emissions_Avion_g_km"]].copy()

def format_passenger_millions(value: float) -> str:
    return f"{value:.1f} M" if value is not None else "0.0 M"
