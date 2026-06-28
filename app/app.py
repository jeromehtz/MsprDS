import os
import sys
from pathlib import Path

import streamlit as st
import requests
import pandas as pd
import os

# =====================
# CONFIG
# =====================
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="ObRail - MSPR Dashboard",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded",
)

import requests
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils import load_co2_comparison, load_station_frequencies, format_passenger_millions

# =====================
# SESSION STATE (AUTH)
# =====================
if "token" not in st.session_state:
    st.session_state.token = None


# =====================
# HELPERS
# =====================

def api_get(endpoint):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return requests.get(f"{API_URL}{endpoint}", headers=headers, timeout=5)


def api_post(endpoint, data):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return requests.post(f"{API_URL}{endpoint}", json=data, headers=headers, timeout=5)


def load_local_stats(country: str):
    stations_df = load_station_frequencies(country)
    co2_df = load_co2_comparison()
    return stations_df, co2_df


def build_stats_payload(country: str, stations_df: pd.DataFrame, co2_df: pd.DataFrame) -> dict:
    top_stations = stations_df.sort_values(by="annual_passengers_millions", ascending=False).head(10)
    summary = {
        "country": country,
        "top_stations": top_stations.to_dict(orient="records"),
        "train_vs_plane_comparison": co2_df[["Pays", "Emissions_Train_g_km", "Emissions_Avion_g_km"]].to_dict(orient="records"),
    }
    if not co2_df.empty:
        best = co2_df.iloc[0]
        summary["top_train_vs_plane_saving"] = {
            "Pays": str(best["Pays"]),
            "Emissions_Train_g_km": float(best["Emissions_Train_g_km"]),
            "Emissions_Avion_g_km": float(best["Emissions_Avion_g_km"]),
            "Savings_g_km": float(best["Emissions_Avion_g_km"] - best["Emissions_Train_g_km"]),
        }
    return summary


def render_api_status():
    st.title("🧪 État de l'API")
    st.write("URL de l'API :", API_URL)
    try:
        res = api_get("/")
        st.write("Code de statut :", res.status_code)
        if res.status_code == 200:
            st.success("API en ligne 🚀")
            st.json(res.json())
        else:
            st.error("API hors ligne ou erreur de réponse.")
    except requests.RequestException:
        st.error("Impossible de joindre l'API. Vérifiez l'URL et le backend.")


# =====================
# SIDEBAR MENU
# =====================
menu = st.sidebar.radio(
    "Navigation",
    ["🏠 Accueil", "🔐 Authentification", "🚆 Trajets", "📊 Statistiques", "🧪 API Status"],
)


# =====================
# PAGE ACCUEIL
# =====================
if menu == "🏠 Accueil":
    st.title("🚆 ObRail - Dashboard Ferroviaire")
    st.markdown(
        """
        ## Observatoire ferroviaire
        Explorez les données de trafic, les émissions CO₂ et les performances des gares.

        Cette application permet de comparer les impacts environnementaux du train et de l'avion,
        tout en présentant les gares les plus fréquentées.
        """
    )

    try:
        res = api_get("/")
        if res.status_code == 200:
            st.success("API accessible — prêt à l'emploi")
        else:
            st.warning("API accessible, mais la vérification a échoué.")
    except requests.RequestException:
        st.error("API inaccessible. Vérifiez que le backend tourne sur l'URL configurée.")

    st.markdown(
        """
        - **Accessibilité** : sections clairement séparées et labels explicites.
        - **Visualisations** : tableaux, graphiques et comparaisons CO₂.
        - **Transparence des sources** : données chargées à partir des fichiers du dépôt.
        """
    )


# =====================
# PAGE AUTH
# =====================
elif menu == "🔐 Authentification":
    st.title("🔐 Authentification")
    st.markdown("Veuillez vous connecter ou créer un compte pour accéder aux fonctionnalités protégées.")

    tab1, tab2 = st.tabs(["Connexion", "Inscription"])

    with tab1:
        username = st.text_input("Nom d'utilisateur", key="login_username", help="Saisissez votre identifiant utilisateur.")
        password = st.text_input("Mot de passe", type="password", key="login_password", help="Saisissez votre mot de passe en toute sécurité.")

        if st.button("Se connecter"):
            res = api_post("/auth/login", {"username": username, "password": password})
            if res.status_code == 200:
                st.session_state.token = res.json().get("access_token")
                st.success("Connexion réussie")
            else:
                st.error("Erreur de connexion")

    with tab2:
        username_r = st.text_input("Nom d'utilisateur", key="register_username", help="Choisissez un nom d'utilisateur.")
        password_r = st.text_input("Mot de passe", type="password", key="register_password", help="Choisissez un mot de passe.")

        if st.button("Créer un compte"):
            res = api_post("/auth/register", {"username": username_r, "password": password_r})
            if res.status_code == 200:
                st.success("Compte créé avec succès")
            else:
                st.error("Erreur de création du compte")


# =====================
# PAGE TRAJETS
# =====================
elif menu == "🚆 Trajets":
    st.title("🚆 Gestion des trajets")
    st.markdown("Consultez les trajets ferroviaires et leurs indicateurs.")

    try:
        res = api_get("/trajets")
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                if "distance" in df.columns:
                    st.subheader("Distribution des distances")
                    st.bar_chart(df["distance"].fillna(0))
            else:
                st.json(data)
        else:
            st.error("Impossible de récupérer les trajets depuis l'API.")
    except requests.RequestException:
        st.error("Erreur de connexion à l'API pour le chargement des trajets.")


# =====================
# PAGE STATISTIQUES
# =====================
elif menu == "📊 Statistiques":
    st.title("📊 Statistiques ferroviaires")
    st.markdown("Analyse du trafic de gares et de l'empreinte CO₂ du train vs avion.")

    country = st.selectbox(
        "Choisissez le pays",
        ["france", "italie", "allemagne", "portugal", "suisse"],
        index=0,
        help="Sélectionnez le pays pour afficher la fréquentation des gares.",
    )
    use_api = st.checkbox("Utiliser l'API pour charger les statistiques", value=True)

    stats_data = None
    if use_api:
        try:
            res = api_get(f"/stats/volumes?country={country}")
            if res.status_code == 200:
                stats_data = res.json()
            else:
                st.warning("Impossible de charger les statistiques depuis l'API. Utilisation des données locales en secours.")
        except requests.RequestException:
            st.warning("L'API statistiques est inaccessible. Utilisation des données locales en secours.")

    if stats_data is None:
        try:
            stations_df, co2_df = load_local_stats(country)
            stats_data = build_stats_payload(country, stations_df, co2_df)
        except Exception as exc:
            st.error(f"Erreur lors du chargement des données locales : {exc}")
            stats_data = None

    if stats_data:
        st.header("Top 10 des gares par fréquentation")
        top_df = pd.DataFrame(stats_data["top_stations"])
        if not top_df.empty:
            top_df["annual_passengers_millions"] = top_df["annual_passengers_millions"].astype(float)
            top_df["passagers"] = top_df["annual_passengers_millions"].apply(format_passenger_millions)
            st.dataframe(
                top_df[["station_name", "city", "region", "annual_passengers_millions", "passagers"]],
                use_container_width=True,
            )
            st.subheader("Volumétrie par gare")
            st.bar_chart(top_df.set_index("station_name")["annual_passengers_millions"])
            st.caption("Les 10 gares les plus fréquentées selon le fichier de fréquentation sélectionné.")
        else:
            st.info("Aucune donnée de gares disponible pour cette sélection.")

        if stats_data.get("train_vs_plane_comparison"):
            st.header("Comparaison CO₂ : train vs avion")
            compare_df = pd.DataFrame(stats_data["train_vs_plane_comparison"])
            if not compare_df.empty:
                compare_df = compare_df.dropna(subset=["Emissions_Train_g_km", "Emissions_Avion_g_km"])
                compare_df["Emissions_Train_g_km"] = compare_df["Emissions_Train_g_km"].astype(float)
                compare_df["Emissions_Avion_g_km"] = compare_df["Emissions_Avion_g_km"].astype(float)
                st.dataframe(compare_df, use_container_width=True)
                compare_chart = compare_df.set_index("Pays")[["Emissions_Train_g_km", "Emissions_Avion_g_km"]]
                if not compare_chart.empty:
                    st.bar_chart(compare_chart)
                    st.caption("Comparaison des émissions de CO₂ par km pour le train et l'avion.")

        top_saving = stats_data.get("top_train_vs_plane_saving")
        if top_saving:
            st.markdown(
                f"**Plus grand écart train vs avion :** {top_saving['Pays']} — train : {top_saving['Emissions_Train_g_km']} g/km, avion : {top_saving['Emissions_Avion_g_km']} g/km, économie : {top_saving['Savings_g_km']} g/km."
            )

        with st.expander("Sources des données et méthode"):
            st.markdown(
                """
                - `data/co2_comparaison_europe.csv` : comparaison des émissions CO₂ par pays.
                - `data/frequentation_gares/frequentation_gares_<pays>.csv` : fréquentation annuelle des gares.
                - Route API `/stats/volumes` : volume de passagers et comparaison train/avion.
                """
            )
    else:
        st.error("Impossible d'afficher les statistiques pour le moment.")


# =====================
# PAGE API STATUS
# =====================
elif menu == "🧪 API Status":
    render_api_status()
