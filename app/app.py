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
    layout="wide"
)

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

    return requests.get(f"{API_URL}{endpoint}", headers=headers)


def api_post(endpoint, data):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    return requests.post(f"{API_URL}{endpoint}", json=data, headers=headers)


# =====================
# SIDEBAR MENU
# =====================
menu = st.sidebar.radio(
    "Navigation",
    ["🏠 Accueil", "🔐 Authentification", "🚆 Trajets", "🧪 API Status"]
)

# =====================
# PAGE ACCUEIL
# =====================
if menu == "🏠 Accueil":
    st.title("🚆 ObRail - Dashboard Ferroviaire")

    res = api_get("/")

    if res.status_code == 200:
        st.success(res.json()["message"])
    else:
        st.error("API inaccessible")

    st.markdown("""
    ### 🎯 Fonctionnalités
    - Gestion des utilisateurs (auth)
    - Consultation des trajets ferroviaires
    - Analyse des données transport
    """)

# =====================
# PAGE AUTH
# =====================
elif menu == "🔐 Authentification":
    st.title("🔐 Authentification")

    tab1, tab2 = st.tabs(["Login", "Register"])

    # ---------------- LOGIN ----------------
    with tab1:
        username = st.text_input("Nom d'utilisateur", key="login_username")
        password = st.text_input("Mot de passe", type="password", key="login_password")

        if st.button("Se connecter"):
            res = api_post("/auth/login", {
                "username": username,
                "password": password
            })

            if res.status_code == 200:
                st.session_state.token = res.json().get("access_token")
                st.success("Connexion réussie")
            else:
                st.error("Erreur de connexion")

    # ---------------- REGISTER ----------------
    with tab2:
        username_r = st.text_input("Nom d'utilisateur", key="register_username")
        password_r = st.text_input("Mot de passe", type="password", key="register_password")

        if st.button("Créer compte"):
            res = api_post("/auth/register", {
                "username": username_r,
                "password": password_r
            })

            if res.status_code == 200:
                st.success("Compte créé avec succès")
            else:
                st.error("Erreur création compte")


# =====================
# PAGE TRAJETS
# =====================
elif menu == "🚆 Trajets":
    st.title("🚆 Gestion des trajets")

    res = api_get("/trajets")  # endpoint attendu dans trajet_router

    if res.status_code == 200:
        data = res.json()

        if isinstance(data, list):
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

            # Exemple simple de stats si champs existants
            if "distance" in df.columns:
                st.bar_chart(df["distance"])
        else:
            st.json(data)

    else:
        st.error("Impossible de récupérer les trajets")


# =====================
# PAGE API STATUS
# =====================
elif menu == "🧪 API Status":
    st.title("🧪 État de l'API")

    res = api_get("/")

    st.write("Status code:", res.status_code)

    if res.status_code == 200:
        st.success("API en ligne 🚀")
        st.json(res.json())
    else:
        st.error("API hors ligne")