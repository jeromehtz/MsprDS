import streamlit as st
import requests
import pandas as pd
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
def api_get(endpoint, params=None):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    return requests.get(f"{API_URL}{endpoint}", headers=headers, params=params)


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
    [
        "🏠 Accueil",
        "🔐 Authentification",
        "🚆 Trajets",
        "🔮 Prédiction CO₂",
        "📊 KPI & Graphiques",
        "🩺 Monitoring",
        "🧪 API Status",
    ]
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
    st.title("🚆 Consultation & filtrage des trajets")

    if not st.session_state.token:
        st.warning("🔐 Connectez-vous (page Authentification) pour consulter les trajets.")
    else:
        filters_res = api_get("/trajets/filters")
        filters = filters_res.json() if filters_res.status_code == 200 else {
            "years": [], "service_types": [], "origin_regions": [], "destination_regions": []
        }

        with st.expander("🔎 Filtres", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                year = st.selectbox("Année", ["(toutes)"] + filters["years"])
                service = st.selectbox("Type de service", ["(tous)"] + filters["service_types"])
            with c2:
                o_region = st.selectbox("Région d'origine", ["(toutes)"] + filters["origin_regions"])
                d_region = st.selectbox("Région de destination", ["(toutes)"] + filters["destination_regions"])
            with c3:
                search = st.text_input("Recherche gare (origine/destination)")
                limit = st.slider("Nombre max de résultats", 50, 5000, 500, step=50)

        params = {"limit": limit}
        if year != "(toutes)":
            params["year"] = year
        if service != "(tous)":
            params["service_type"] = service
        if o_region != "(toutes)":
            params["origin_region"] = o_region
        if d_region != "(toutes)":
            params["destination_region"] = d_region
        if search:
            params["search"] = search

        res = api_get("/trajets/", params=params)

        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame(data)

            st.caption(f"**{len(df)}** trajet(s) affiché(s)")

            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)

                if "passengers_millions" in df.columns and "year" in df.columns:
                    st.subheader("Voyageurs (M) par année — sélection courante")
                    serie = df.groupby("year")["passengers_millions"].sum().sort_index()
                    st.bar_chart(serie)
            else:
                st.info("Aucun trajet ne correspond à ces filtres.")
        else:
            st.error("Impossible de récupérer les trajets")


# =====================
# PAGE PREDICTION CO2
# =====================
elif menu == "🔮 Prédiction CO₂":
    st.title("🔮 Prédiction de l'empreinte CO₂")
    st.caption("Modèle XGBoost — comparaison train / voiture / avion")

    if not st.session_state.token:
        st.warning("🔐 Connectez-vous (page Authentification) pour utiliser la prédiction.")
    else:
        opt_res = api_get("/predict/options")

        if opt_res.status_code != 200:
            st.error("Impossible de charger les options du modèle.")
        else:
            opt = opt_res.json()

            m = opt.get("metrics", {})
            c1, c2, c3 = st.columns(3)
            c1.metric("R²", f"{m.get('R2', 0):.4f}")
            c2.metric("MAE (g/km)", f"{m.get('MAE', 0):.3f}")
            c3.metric("RMSE (g/km)", f"{m.get('RMSE', 0):.3f}")
            st.caption(f"Source du modèle : **{opt.get('model_source', 'Local (.pkl)')}**")

            with st.form("prediction_form"):
                col1, col2 = st.columns(2)
                with col1:
                    origin = st.selectbox("Gare de départ", opt["stations"])
                    service = st.selectbox("Type de service", opt["service_types"])
                    year = st.number_input("Année", 2016, 2030, 2024)
                    heure = st.slider("Heure de départ", 0, 23, 9)
                with col2:
                    destination = st.selectbox("Gare d'arrivée", opt["stations"])
                    jour = st.selectbox("Jour de la semaine", opt["jours_semaine"])
                    mois = st.slider("Mois", 1, 12, 6)
                    passengers = st.number_input("Voyageurs (millions)", 0.0, 100.0, 1.0)

                distance = st.number_input(
                    "Distance du trajet (km) — pour le total par mode",
                    0, 5000, 430
                )
                ferie = st.checkbox("Jour férié")
                submit = st.form_submit_button("Prédire l'empreinte CO₂")

            if submit:
                payload = {
                    "origin_station": origin,
                    "destination_station": destination,
                    "service_type": service,
                    "year": int(year),
                    "passengers_millions": float(passengers),
                    "heure": int(heure),
                    "jour_semaine": jour,
                    "mois": int(mois),
                    "est_jour_ferie": 1 if ferie else 0,
                    "distance_km": float(distance) if distance else None,
                }
                res = api_post("/predict/co2", payload)

                if res.status_code == 200:
                    data = res.json()

                    st.subheader("Émissions par mode (g CO₂ / km)")
                    k1, k2, k3 = st.columns(3)
                    k1.metric("🚆 Train", f"{data['train_g_km']:.2f}")
                    k2.metric("🚗 Voiture", f"{data['car_g_km']:.2f}")
                    k3.metric("✈️ Avion", f"{data['plane_g_km']:.2f}")

                    df_km = pd.DataFrame(
                        {"g_CO2_par_km": [data["train_g_km"], data["car_g_km"], data["plane_g_km"]]},
                        index=["🚆 Train", "🚗 Voiture", "✈️ Avion"],
                    )
                    st.bar_chart(df_km)

                    st.success(
                        f"✅ Le train évite **{data['co2_saved_vs_car_g_km']:.1f} g/km** "
                        f"vs voiture et **{data['co2_saved_vs_plane_g_km']:.1f} g/km** vs avion."
                    )

                    if data.get("distance_km"):
                        st.subheader(f"Total du trajet ({data['distance_km']:.0f} km) — kg CO₂")
                        df_total = pd.DataFrame(
                            {"kg_CO2": [data["total_train_kg"], data["total_car_kg"], data["total_plane_kg"]]},
                            index=["🚆 Train", "🚗 Voiture", "✈️ Avion"],
                        )
                        st.bar_chart(df_total)
                else:
                    st.error(f"Erreur de prédiction ({res.status_code})")


# =====================
# PAGE KPI & GRAPHIQUES
# =====================
elif menu == "📊 KPI & Graphiques":
    st.title("📊 Indicateurs clés & graphiques")

    if not st.session_state.token:
        st.warning("🔐 Connectez-vous (page Authentification) pour consulter les indicateurs.")
    else:
        res = api_get("/stats/kpi")

        if res.status_code != 200:
            st.error("Impossible de récupérer les indicateurs.")
        else:
            kpi = res.json()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Voyageurs (M)", f"{kpi['total_passengers_millions']:,.0f}")
            c2.metric("Liaisons", f"{kpi['nb_routes']:,}")
            c3.metric("Types de service", kpi["nb_service_types"])
            years = kpi["years_covered"]
            c4.metric("Période", f"{years[0]}–{years[-1]}" if years else "—")

            st.subheader("Répartition jour / nuit")
            period = kpi.get("by_period", {})
            if period:
                pcol1, pcol2 = st.columns([1, 2])
                with pcol1:
                    st.metric("☀️ Jour (M)", f"{period.get('Jour', 0):,.0f}")
                    st.metric("🌙 Nuit (M)", f"{period.get('Nuit', 0):,.0f}")
                with pcol2:
                    st.bar_chart(pd.Series(period, name="Voyageurs (M)"))
                st.caption(
                    "Classification dérivée du type de service. Le jeu de données principal "
                    "ne contient que des services de jour."
                )

            st.subheader("Volume de voyageurs par type de service")
            if kpi["by_service_type"]:
                st.bar_chart(pd.Series(kpi["by_service_type"], name="Voyageurs (M)"))

            st.subheader("Évolution annuelle du volume de voyageurs")
            if kpi["by_year"]:
                serie = pd.Series(
                    {int(k): v for k, v in kpi["by_year"].items()}, name="Voyageurs (M)"
                ).sort_index()
                st.line_chart(serie)

            st.subheader("Top 10 des régions d'origine")
            if kpi["by_origin_region_top10"]:
                st.bar_chart(pd.Series(kpi["by_origin_region_top10"], name="Voyageurs (M)"))

            st.subheader("Top 10 des axes les plus fréquentés")
            if kpi["top_routes"]:
                df_routes = pd.DataFrame(kpi["top_routes"])
                df_routes.columns = ["Origine", "Destination", "Voyageurs (M)"]
                st.dataframe(df_routes, use_container_width=True, hide_index=True)


# =====================
# PAGE MONITORING
# =====================
elif menu == "🩺 Monitoring":
    st.title("🩺 Santé du service & incidents")

    # État de santé (endpoint public)
    health_res = api_get("/monitoring/health")
    if health_res.status_code == 200:
        h = health_res.json()
        hc1, hc2, hc3 = st.columns(3)
        ok = h["status"] == "ok"
        hc1.metric("Service", "🟢 OK" if ok else "🔴 Dégradé")
        hc2.metric("API", "🟢 up" if h["api"] == "up" else "🔴 down")
        hc3.metric("Base de données", "🟢 up" if h["database"] == "up" else "🔴 down")
        if ok:
            st.success("Tous les composants sont opérationnels.")
        else:
            st.error("⚠️ Service dégradé — voir l'état des composants ci-dessus.")
    else:
        st.error("🔴 Service injoignable (health check en échec).")

    st.divider()

    if not st.session_state.token:
        st.info("🔐 Connectez-vous pour voir le détail du trafic et des incidents.")
    else:
        summary_res = api_get("/monitoring/summary")
        if summary_res.status_code == 200:
            s = summary_res.json()

            m1, m2, m3 = st.columns(3)
            m1.metric("Requêtes totales", f"{s['total_requests']:,}")
            m2.metric("Incidents (4xx/5xx)", f"{s['error_count']:,}")
            m3.metric("Taux d'erreur", f"{s['error_rate_pct']:.2f} %")

            st.subheader("Répartition des réponses par statut HTTP")
            if s["by_status"]:
                st.bar_chart(pd.Series(s["by_status"], name="Requêtes"))

            st.subheader("Incidents détectés")
            if s["incidents"]:
                df_inc = pd.DataFrame(s["incidents"])
                df_inc.columns = ["Endpoint [statut]", "Occurrences"]
                st.dataframe(df_inc, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Aucun incident (4xx/5xx) détecté.")
        else:
            st.error("Impossible de récupérer la synthèse du monitoring.")

    st.divider()
    st.caption(
        "📊 Tableaux de bord détaillés : "
        "[Grafana](http://localhost:3000) · [Prometheus](http://localhost:9090)"
    )


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