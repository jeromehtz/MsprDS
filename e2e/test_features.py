"""
Tests E2E de parcours complet : authentification via l'UI, puis utilisation des
pages Prédiction CO₂ et KPI & Graphiques (vérifie le flux jusqu'au backend).
"""

import uuid

import pytest

pytestmark = pytest.mark.e2e

# Username unique par exécution : le compte est toujours créé à neuf,
# indépendamment de l'état de la base (qui peut persister entre les runs).
USERNAME = f"e2e_{uuid.uuid4().hex[:10]}"
PASSWORD = "e2e_pass123"


def _set_field(page, label, index, value):
    """Renseigne un champ Streamlit puis blur (Tab) pour que la valeur soit committée."""
    field = page.get_by_label(label).nth(index)
    field.click()
    field.fill(value)
    field.press("Tab")


def _login_via_ui(page):
    """Crée un compte (idempotent) puis se connecte via l'interface Streamlit."""
    page.get_by_test_id("stSidebar").get_by_text("Authentification").click()
    page.wait_for_selector("text=Register", timeout=10000)

    # --- Register (l'onglet Register est le 2e jeu de champs) ---
    page.get_by_role("tab", name="Register").click()
    _set_field(page, "Nom d'utilisateur", 1, USERNAME)
    _set_field(page, "Mot de passe", 1, PASSWORD)
    page.get_by_role("button", name="Créer compte").click()
    page.wait_for_timeout(1500)  # laisse Streamlit traiter (création ou doublon)

    # --- Login (1er jeu de champs) ---
    page.get_by_role("tab", name="Login").click()
    _set_field(page, "Nom d'utilisateur", 0, USERNAME)
    _set_field(page, "Mot de passe", 0, PASSWORD)
    page.get_by_role("button", name="Se connecter").click()
    page.wait_for_selector("text=Connexion réussie", timeout=10000)


def test_kpi_page_after_login(app_page):
    _login_via_ui(app_page)
    app_page.get_by_test_id("stSidebar").get_by_text("KPI").click()
    # Les indicateurs (st.metric) s'affichent une fois authentifié
    app_page.wait_for_selector('[data-testid="stMetric"]', timeout=15000)
    assert app_page.locator('[data-testid="stMetric"]').count() >= 1


def test_trajets_filter_after_login(app_page):
    _login_via_ui(app_page)
    app_page.get_by_test_id("stSidebar").get_by_text("Trajets").click()
    # Le panneau de filtres s'affiche une fois authentifié (après chargement des filtres)
    app_page.wait_for_selector("text=Filtres", timeout=15000)
    service_filter = app_page.get_by_text("Type de service").first
    service_filter.wait_for(state="visible", timeout=15000)
    assert service_filter.is_visible()

def capture_request(request):
    print(request.url)
    if "/predict/co2" in request.url:
        print("\n===== API REQUEST =====")
        print(request.method)
        print(request.url)
        print("BODY:", request.post_data)
        print("=======================\n")


def capture_response(response):
    print(response.url)
    if "/predict/co2" in response.url:
        print("\n===== API RESPONSE =====")
        print(response.status)
        print(response.url)
        print("BODY:", response.text())
        print("========================\n")



def test_prediction_page_after_login(app_page):
    _login_via_ui(app_page)

    app_page.get_by_test_id("stSidebar").get_by_text("Prédiction").click()

    app_page.wait_for_selector(
        "text=Prédire l'empreinte CO",
        timeout=15000
    )

    app_page.on("request", capture_request)
    app_page.on("response", capture_response)

    app_page.get_by_role(
        "button",
        name="Prédire l'empreinte CO₂"
    ).click()

    # DEBUG
    app_page.wait_for_timeout(3000)
    print("\n========== CONTENU PREDICTION ==========")
    
    print(app_page.locator("body").inner_text())
    print("=========================================\n")

    app_page.wait_for_selector(
        "text=Émissions par mode",
        timeout=20000
    )
