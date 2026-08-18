from playwright.sync_api import sync_playwright
import requests
import re


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "http://localhost:8501"
API_URL = "http://127.0.0.1:8000"

USERNAME = "azertyuiop"
PASSWORD = "azertyuiop123"


# ============================================================
# VÉRIFICATION API
# ============================================================

def check_api():
    print("\n========== VÉRIFICATION API ==========")
    print("URL :", API_URL)

    try:
        response = requests.get(
            f"{API_URL}/",
            timeout=5
        )

        print("STATUS :", response.status_code)

        assert response.status_code < 500, (
            f"L'API répond avec une erreur HTTP "
            f"{response.status_code}"
        )

        print("✅ API disponible")

    except requests.RequestException as e:
        raise AssertionError(
            f"\n❌ API inaccessible sur {API_URL}\n"
            f"Erreur : {e}\n\n"
            f"Assure-toi que FastAPI est lancé avant le test."
        )


# ============================================================
# REMPLISSAGE DES CHAMPS
# ============================================================

def _set_field(page, label, index, value):

    field = page.get_by_label(label).nth(index)

    field.fill(value)

    print(
        f"{label} rempli :",
        repr(field.input_value())
    )

    field.blur()

    page.wait_for_timeout(500)


# ============================================================
# LOG REQUÊTE API
# ============================================================

def log_request(request):

    print("\n>>> REQUEST API")

    print("METHOD :", request.method)
    print("URL    :", request.url)
    print("DATA   :", request.post_data)


# ============================================================
# LOG RÉPONSE API
# ============================================================

def log_response(response):

    print("\n<<< RESPONSE API")

    print("STATUS :", response.status)
    print("URL    :", response.url)

    try:
        print("BODY   :", response.text())

    except Exception as e:

        print(
            "BODY   : impossible à lire :",
            e
        )


# ============================================================
# LOGIN VIA L'INTERFACE STREAMLIT
# ============================================================

def _login_via_ui(page):

    print("\n========== DEBUG IDENTIFIANTS ==========")

    print("USERNAME :", USERNAME)
    print("PASSWORD :", PASSWORD)

    print("========================================")

    # ========================================================
    # ACTIVATION DES LOGS RÉSEAU
    # ========================================================

    page.on("request", log_request)
    page.on("response", log_response)

    # ========================================================
    # AUTHENTIFICATION
    # ========================================================

    print("\n========== AUTHENTIFICATION ==========")

    page.get_by_test_id(
        "stSidebar"
    ).get_by_text(
        "Authentification"
    ).click()

    page.wait_for_selector(
        "text=Register",
        timeout=10000
    )

    # ========================================================
    # REGISTER
    # ========================================================

    print("\n========== REGISTER ==========")

    page.get_by_role(
        "tab",
        name="Register"
    ).click()

    _set_field(
        page,
        "Nom d'utilisateur",
        1,
        USERNAME
    )

    _set_field(
        page,
        "Mot de passe",
        1,
        PASSWORD
    )

    print(
        "\n--- VALEURS DES INPUTS APRÈS REMPLISSAGE ---"
    )

    inputs = page.locator("input")

    print(
        "Nombre total d'inputs :",
        inputs.count()
    )

    # ========================================================
    # CRÉATION DU COMPTE
    # ========================================================

    print("\n--- CLIC CRÉER COMPTE ---")

    page.get_by_role(
        "button",
        name="Créer compte"
    ).click()

    print("Clic effectué.")

    page.wait_for_timeout(3000)

    # ========================================================
    # APRÈS REGISTER
    # ========================================================

    print("\n========== APRÈS REGISTER ==========")

    print("URL :", page.url)

    page.screenshot(
        path="e2e/after_register.png",
        full_page=True
    )

    # ========================================================
    # RÉCUPÉRATION DES ALERTES
    # ========================================================

    all_alerts = page.locator(
        '[data-testid="stAlert"]'
    )

    page.wait_for_timeout(1000)

    print(
        f"\nAlertes trouvées : {all_alerts.count()}"
    )

    for i in range(all_alerts.count()):

        print(
            f"  Alerte {i} :",
            repr(
                all_alerts.nth(i).inner_text()
            )
        )

    # ========================================================
    # VÉRIFICATION SUCCÈS REGISTER
    # ========================================================

    success_alert = page.locator(
        '[data-testid="stAlert"]'
    ).filter(
        has_text=re.compile(
            "succès|réussi",
            re.IGNORECASE
        )
    )

    assert success_alert.count() > 0, (
        "Aucun message de succès détecté."
    )

    print("✅ Inscription réussie")

    # ========================================================
    # LOGIN
    # ========================================================

    print("\n========== LOGIN ==========")

    print("USERNAME :", USERNAME)
    print("PASSWORD :", PASSWORD)

    print("============================")

    page.get_by_role(
        "tab",
        name="Login"
    ).click()

    _set_field(
        page,
        "Nom d'utilisateur",
        0,
        USERNAME
    )

    _set_field(
        page,
        "Mot de passe",
        0,
        PASSWORD
    )

    print("\n--- VALEURS LOGIN ---")

    print("\n--- CLIC SE CONNECTER ---")

    page.get_by_role(
        "button",
        name="Se connecter"
    ).click()

    # ========================================================
    # VÉRIFICATION MESSAGE LOGIN
    # ========================================================

    alert_or_toast = page.locator(
        '[data-testid="stAlert"], '
        '[data-testid="stToast"]'
    )

    try:

        page.wait_for_timeout(1000)

        text = alert_or_toast.first.inner_text()

        print(
            "Message détecté :",
            repr(text)
        )

        assert text.strip() != "", (
            "Message vide"
        )

    except Exception:

        page.screenshot(
            path="e2e/login_failed.png",
            full_page=True
        )

        raise

    # ========================================================
    # APRÈS LOGIN
    # ========================================================

    print("\n========== APRÈS LOGIN ==========")

    print("URL :", page.url)

    page.screenshot(
        path="e2e/debug_apres_login.png",
        full_page=True
    )

    print("✅ Login terminé")


# ============================================================
# TEST LOGIN LOCAL
# ============================================================

def test_login_local():

    print("\n")
    print("=" * 60)
    print("              TEST E2E LOGIN LOCAL")
    print("=" * 60)
    # ========================================================
    # VÉRIFICATION API
    # ========================================================
    check_api()
    # ========================================================
    # PLAYWRIGHT
    # =======================================================
    print("\n========== DÉMARRAGE PLAYWRIGHT ==========")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False
        )
        page = browser.new_page()
        # ====================================================
        # OUVERTURE STREAMLIT
        # ====================================================

        print("\n========== OUVERTURE STREAMLIT ==========")
        print("URL :", BASE_URL)
        page.goto(BASE_URL)

        page.wait_for_load_state(
            "networkidle"
        )

        print("✅ Streamlit chargé")
        # ====================================================
        # AUTHENTIFICATION
        # ====================================================

        _login_via_ui(page)
        print("\n")
        print("=" * 60)
        print("          ✅ CONNEXION RÉUSSIE !")
        print("=" * 60)

        # ====================================================
        # FERMETURE NAVIGATEUR
        # ====================================================
        browser.close()
        print("✅ Navigateur fermé")